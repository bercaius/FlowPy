# FlowPy — Professional Python IDE with Live Flowchart View

**FlowPy** is a modern desktop application for Python development with an
integrated, live-updating flowchart view. Write code in the editor and watch
the flowchart panel sync in real time.

**Developed by [TurcoDevelopStudio](https://bercaius.github.io/turcodevelop-studio/)**
© Berkay Özdemir — [@bercaius](https://github.com/bercaius)

---

## Features

- **Secure project vault**: all projects stored safely in AppData
- **Multi-file editor**: tabbed editing, syntax highlighting
- **Live flowchart sync**: edit code and the flowchart updates automatically
- **Professional flowchart renderer**: large, high-contrast nodes
- **Built-in terminal**: run scripts with live output
- **File explorer**: browse project files
- **Export**: save flowchart as PNG

## Getting Started

```bash
cd windows
pip install -r requirements.txt
python main.py
```

## Building for Distribution

```bash
python build.py
python build_installer.py
```

## Architecture

```
windows/
├── main.py                  # Entry point
├── app.py                   # Professional startup (logging, splash, exceptions)
├── build.py                 # PyInstaller build script
├── build_installer.py       # Inno Setup installer builder
├── requirements.txt
├── assets/                  # Brand logos and banners
├── flowpy/
│   ├── core/                # Services, settings, project, runner, builder
│   ├── plugins/             # Plugin system (base, discovery, manager, builtin)
│   ├── ui/                  # Main window, flowchart, dialogs
│   └── resources/           # Styles, icons
└── installer/
    └── flowpy.iss           # Inno Setup script
```

## License

MIT
