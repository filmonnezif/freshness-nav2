#!/usr/bin/env python3
"""Standalone executable for isolated guard filter node processes."""
import argparse
import sys
from pathlib import Path
import rclpy
from rclpy.executors import SingleThreadedExecutor

# Import modular guard filter
from guards import ModularFreshnessFilter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=str, required=True)
    parser.add_argument('--mode', type=str, required=True)
    parser.add_argument('--guards', nargs='*', default=[])
    args = parser.parse_args()

    rclpy.init()
    node = ModularFreshnessFilter(
        prefix=args.prefix,
        mode_name=args.mode,
        enabled_guards=set(args.guards)
    )
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        executor.shutdown()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
