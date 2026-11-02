import os
import tempfile

# Must run before airsense is imported anywhere: isolate data dir and keep demo data small.
os.environ["AIRSENSE_DATA_DIR"] = tempfile.mkdtemp(prefix="airsense_test_")
os.environ["AIRSENSE_DEMO_DAYS"] = "150"
