# Full-building live coverage decision

Date: 2026-08-23

The current deployment configuration in `model_server/config/cameras.yaml` defines three sources: `cam_001`, `cam_002`, and `cam_003`. No source definitions or credentials were supplied for `cam_004` through `cam_155`.

Decision for this release: additional sources will not be configured. All 155 canonical room/camera mappings remain stable; unconfigured cameras are returned as `offline` with unavailable occupancy. They are never omitted or renumbered. Adding future sources is a configuration change using the existing canonical IDs and does not require a frontend mode.

This policy is tested in both mock and database repository contract suites.
