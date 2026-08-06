# OrthoRoute 1.0.0 for KiCad

This is a native KiCad IPC plugin.

1. Copy `com.github.bbenchoff.orthoroute` into the KiCad `<version>/plugins` directory.
2. In KiCad, enable the API server under Preferences > Plugins.
3. Restart PCB Editor and wait for the plugin environment to finish installing.
4. Launch OrthoRoute from the PCB Editor toolbar.

KiCad installs the dependencies in `requirements.txt` into an isolated
environment. The first load can take several minutes because the GUI and GPU
runtime wheels are large.
