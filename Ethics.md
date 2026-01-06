# Ethics Statement

## IMPORTANT: Ethic will be fulfilled by the V1.0 releases. Versions before v1.0 may not have all ethics involved

This project explores limited, opt-in AI augmentation within live improvisational theater under strict ethical constraints. These constraints are foundational to the system’s design and operation.

## Human Control and Agency'

- Human performers and operators always retain full creative and operational control.
- AI output is **only** produced when explicitly triggered by a human-operated control.
- A clearly accessible **kill switch** is present at all times and immediately disables AI output.
- The system cannot initiate dialogue, actions, or scene changes autonomously.

## Data Handling and Privacy

- Voice, video, and sensor data are **not retained** beyond the duration of a single performance.
- No persistent storage occurs during normal operation.
- Logging is minimized and restricted to operational needs only.
- Expanded logging and inspection are possible **only** in debug mode.
- Debug mode is always explicitly announced to performers and relevant participants.

## Ethics Mode and Debug Safeguards

- The system includes a dedicated **Ethics Mode** that enforces the exclusive use of copyright-respecting AI tools and models.
- A separate **Standard Mode** may be used for higher technical precision.
- Ethics Mode **disables debug mode** to prevent unintended data retention or inspection.
- Mode selection is deliberate and transparent to operators.

## AI Infrastructure

- The project does **not** use third-party conversational AI APIs (e.g., ChatGPT).
- All processing is performed on locally hosted systems or explicitly provisioned cloud virtual machines.
- Performance data is not transmitted to external services unless explicitly configured for testing.

## Artistic Intent

- This project does **not** claim to solve improvisation, automate creativity, or replace human performers.
- The AI is not a performer, author, or creative authority.
- The system is an experimental augmentation explored in good faith, with respect for artistic labor and cultural concerns surrounding AI in the arts.

## Ongoing Responsibility

- Ethical constraints are treated as first-order design requirements.
- Feedback from performers, collaborators, and audiences is considered essential.
- The project may be revised, paused, or discontinued if these principles are compromised.

## Performer Consent

- All performers are informed in advance when AI augmentation is used.
- Participation is voluntary; performers may opt out of scenes or performances involving AI without penalty.
- No performer is required to interact with, respond to, or incorporate AI output.

## Audience Transparency

- The presence of AI augmentation is disclosed to audiences before or at the start of a performance.
- The project does not conceal AI involvement or present AI-generated output as human-generated.

## Attribution and Authorship

- AI output is not credited as authorship, performance, or creative ownership.
- Creative credit remains solely with the human performers and creators.
- The system does not claim originality, intent, or authorship.

## Content Boundaries

- The system includes constraints intended to prevent hateful, harassing, or unsafe output.
- Human operators actively monitor AI output during performances.
- The kill switch serves as an immediate safeguard against inappropriate or unintended content.

## Accountability

- Human operators are fully responsible for all AI output during a performance.
- Responsibility for content, timing, and usage rests with the project operators, not the system itself.

## Ethics FAQ

**Does this replace human performers?**
No. Human performers retain full control. The AI cannot act, speak, or influence a scene without explicit human input.

**Is the AI improvising on its own?**
No. The AI does not initiate content. It responds only when triggered by a human operator.

**Is audience or performer data stored or reused?**
No. Data is show-persistent only and discarded after the performance unless debug mode is explicitly enabled and announced.

**What is debug mode, and when is it used?**
Debug mode enables additional logging for development and testing. It is always announced and never active during Ethics Mode.

**What is Ethics Mode?**
Ethics Mode enforces the use of copyright-respecting AI tools and disables debug functionality to ensure privacy and data minimization.

**Are third-party AI APIs used?**
No. The system does not rely on external conversational AI services. All processing occurs locally or on controlled cloud infrastructure.

**Why use AI at all?**
The project is an optional experiment in augmentation, not a solution to a problem or a replacement for human creativity.

**Can the AI be shut off mid-show?**
Yes. A physical or software kill switch is always available and immediately disables AI output.

**I found a problem with the ethics implementation. What should I do?**
Please open an issue on the project repository. Feedback is essential to uphold ethical standards.
