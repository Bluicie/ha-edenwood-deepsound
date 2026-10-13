"""Constants for the Edenwood Deep Sound integration."""

from datetime import timedelta

DOMAIN = "edenwood_deepsound"

# The dongle accepts one BLE connection and the remote needs it too, so we only connect briefly.
POLL_INTERVAL = timedelta(minutes=5)
PRESENCE_INTERVAL = timedelta(seconds=2)

# While anything is connected the dongle stops advertising. If it has been quiet this long and it
# wasn't us, the remote is in use; when it advertises again we refresh to pick up its changes.
REMOTE_ACTIVE_AFTER = 4.0
