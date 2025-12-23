# AI Improv ToolKit

Toolkit/Software use to run the AI power show for my local community improv team.

## Ethics Statement

### IMPORTANT: Ethic will be fulfilled by the V1.0 releases. Subsequent version before v1.0 may not have all ethics involved.

This project explores limited, opt-in AI augmentation within live improvisational theater under strict ethical constraints. These constraints are foundational to the system’s design and operation.

### Human Control and Agency
- Human performers and operators always retain full creative and operational control.
- AI output is **only** produced when explicitly triggered by a human-operated control.
- A clearly accessible **kill switch** is present at all times and immediately disables AI output.
- The system cannot initiate dialogue, actions, or scene changes autonomously.

### Data Handling and Privacy
- Voice, video, and sensor data are **not retained** beyond the duration of a single performance.
- No persistent storage occurs during normal operation.
- Logging is minimized and restricted to operational needs only.
- Expanded logging and inspection are possible **only** in debug mode.
- Debug mode is always explicitly announced to performers and relevant participants.

### Ethics Mode and Debug Safeguards
- The system includes a dedicated **Ethics Mode** that enforces the exclusive use of copyright-respecting AI tools and models.
- A separate **Standard Mode** may be used for higher technical precision.
- Ethics Mode **disables debug mode** to prevent unintended data retention or inspection.
- Mode selection is deliberate and transparent to operators.

### AI Infrastructure
- The project does **not** use third-party conversational AI APIs (e.g., ChatGPT).
- All processing is performed on locally hosted systems or explicitly provisioned cloud virtual machines.
- Performance data is not transmitted to external services unless explicitly configured for testing.

### Artistic Intent
- This project does **not** claim to solve improvisation, automate creativity, or replace human performers.
- The AI is not a performer, author, or creative authority.
- The system is an experimental augmentation explored in good faith, with respect for artistic labor and cultural concerns surrounding AI in the arts.

### Ongoing Responsibility
- Ethical constraints are treated as first-order design requirements.
- Feedback from performers, collaborators, and audiences is considered essential.
- The project may be revised, paused, or discontinued if these principles are compromised.

See ETHICS_FAQ.md for more info

## Development Standards

- LF line endings enforced via .gitattributes
- Python formatted with (TODO)
- Terraform formatted with terraform fmt
- pre-commit hooks required (TODO)

## Description

### TODO

## Getting Started

### Dependencies

#### TODO

* Linux Debian 13

### Installing

* How/where to download your program
* Any modifications needed to be made to files/folders

### Executing program

* How to run the program
* Step-by-step bullets
```
code blocks for commands
```

## Help

Any advise for common problems or issues.
```
command to run if program contains helper info
```

## Authors

* Anthony Tilelli

## Version History

* TODO

## License

This project is licensed under the LGPLV3 License - see the LICENSE.md file for details

## Acknowledgments

* [improbotics](https://improbotics.org/)
* [DomPizzie (README template)](https://gist.github.com/DomPizzie/7a5ff55ffa9081f2de27c315f5018afc)
