"""Periodic relay with explicitly selected guards; no shared age-speed scaling."""
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from rosgraph_msgs.msg import Clock
from taxonomy import TAU_CMD, TAU_CLOCK, TAU_SCAN, EPSILON_SKEW

class ModularFreshnessFilter(Node):
    def __init__(self, prefix, mode_name, enabled_guards):
        super().__init__(f'{mode_name}_filter')
        self.enabled_guards = set(enabled_guards)
        self.sim_time = self.last_clock_wall = self.last_progress_wall = None
        self.last_scan_stamp = self.last_cmd_msg = self.last_cmd_wall = None
        self.epoch_invalidated = self.order_invalidated = self.future_invalidated = False
        self.pub = self.create_publisher(Twist, f'{prefix}/{mode_name}/in', 10)
        self.create_subscription(Clock, f'{prefix}/clock', self.on_clock, qos_profile_sensor_data)
        self.create_subscription(LaserScan, f'{prefix}/scan', self.on_scan, qos_profile_sensor_data)
        self.create_subscription(Twist, f'{prefix}/command', self.on_cmd, 10)
        self.steady_clock = RclClock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.02, self.tick, clock=self.steady_clock)

    def on_clock(self, msg):
        now = msg.clock.sec + msg.clock.nanosec * 1e-9
        wall = time.monotonic()
        if 'epoch' in self.enabled_guards and self.sim_time is not None and now < self.sim_time - 1e-6:
            self.epoch_invalidated = True
            self.order_invalidated = self.future_invalidated = False
            self.last_scan_stamp = self.last_cmd_msg = self.last_cmd_wall = None
        if self.sim_time is None or now != self.sim_time:
            self.last_progress_wall = wall
        self.sim_time = now
        self.last_clock_wall = wall

    def on_scan(self, msg):
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if 'future' in self.enabled_guards:
            if self.sim_time is None or stamp > self.sim_time + EPSILON_SKEW:
                self.future_invalidated = True
            if self.future_invalidated:
                return
        if 'order' in self.enabled_guards:
            if self.last_scan_stamp is not None and stamp <= self.last_scan_stamp:
                self.order_invalidated = True
            if self.order_invalidated:
                return
        if self.epoch_invalidated and self.sim_time is not None and -EPSILON_SKEW <= self.sim_time-stamp <= TAU_SCAN:
            self.epoch_invalidated = False
        self.last_scan_stamp = stamp

    def on_cmd(self, msg):
        if not all(math.isfinite(v) for v in (msg.linear.x, msg.linear.y, msg.angular.z)):
            self.last_cmd_msg = self.last_cmd_wall = None
        else:
            self.last_cmd_msg = msg
            self.last_cmd_wall = time.monotonic()

    def tick(self):
        now = time.monotonic()
        blocked = self.last_cmd_msg is None
        if 'cmd' in self.enabled_guards:
            blocked |= self.last_cmd_wall is None or now-self.last_cmd_wall >= TAU_CMD
        if 'clock' in self.enabled_guards:
            blocked |= any(t is None or now-t >= TAU_CLOCK for t in (self.last_clock_wall, self.last_progress_wall))
        blocked |= self.epoch_invalidated or self.order_invalidated or self.future_invalidated
        self.pub.publish(Twist() if blocked else self.last_cmd_msg)
