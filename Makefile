PY ?= python3
FC = research/freshness_contracts

.PHONY: all verify verify-run sensitivity assets paper campaign clean

all: verify sensitivity paper

# Unit tests plus full audits of both recorded campaigns (no ROS needed).
verify:
	$(PY) -m unittest discover -s $(FC) -p 'test_*.py'
	$(PY) $(FC)/build_assets.py --audit-only
	$(PY) $(FC)/build_assets.py --evidence evidence/freshness-contracts-v5-availability \
	  --audit-only --expected-repeats 20 --cases healthy benign_stamp_lag repeated_command

# Offline re-scoring under alternative monitor parameters (paper Table IV).
sensitivity:
	$(PY) $(FC)/sensitivity.py

# Regenerate figures, tables, measurements.csv and RESULTS.md from the raw traces.
assets:
	$(PY) $(FC)/build_assets.py

paper:
	$(MAKE) -C paper

# Re-run the full 80-trial ROS campaign into evidence/reproduction (needs podman or docker).
campaign:
	scripts/run_campaign.sh reproduction --repeats 5

clean:
	$(MAKE) -C paper clean
	find . -name __pycache__ -prune -exec rm -rf {} +

# Audit a new full campaign: make verify-run RUN=reproduction
verify-run:
	$(PY) $(FC)/build_assets.py --evidence evidence/$(RUN) --audit-only
