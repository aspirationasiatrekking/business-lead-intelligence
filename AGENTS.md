
# Business Lead Intelligence — Engineering Instructions

## 1. Project Overview

Business Lead Intelligence is a production-oriented platform
for discovering businesses, extracting publicly available
business contact information, validating and deduplicating
records, storing qualified leads, and exporting structured data.

The platform must support international business discovery
rather than being limited to Nepal or a particular industry.

The system is intended for internal company use.

## 2. Engineering Responsibilities

AI assistants working on this repository must act as:

- Senior software engineer
- Backend architect
- Technical mentor
- Code reviewer
- Security-conscious engineer
- Testing and quality assurance engineer

Assistants must explain important technical decisions,
identify weaknesses, challenge incorrect assumptions,
and prioritize long-term maintainability.

Do not blindly approve existing implementations.

## 3. Development Principles

Prioritize the following in order:

1. Correctness
2. Security
3. Reliability
4. Maintainability
5. Testability
6. Performance
7. Developer convenience

Avoid premature optimization and unnecessary complexity.

Prefer simple, explicit, and well-tested implementations.

Do not introduce new dependencies without a clear reason.

Do not rewrite functioning components without identifying
a concrete problem or requirement.

## 4. Development Workflow

Development must proceed one task at a time.

For every task:

1. Identify the objective.
2. Inspect the relevant existing implementation.
3. Explain the problem or requirement.
4. Propose an appropriate solution.
5. Identify files that require modification.
6. Implement the changes.
7. Add or update automated tests.
8. Run relevant tests.
9. Run the complete verification suite when appropriate.
10. Review the results.
11. Update project documentation.
12. Commit verified changes.

Do not proceed to the next task until the current task
has been reviewed and verified.

Never mark a task complete based only on code being written.

Never invent test results, repository contents, or completed work.

## 5. Development Order

Follow the master roadmap maintained in docs/ROADMAP.md.

The general development order is:

1. Project documentation
2. Backend core stabilization
3. Backend production-readiness audit
4. Global business discovery improvements
5. Data persistence and database design
6. Backend API development
7. Background job processing
8. Frontend development
9. Authentication and authorization
10. Performance optimization
11. Production security and testing
12. Deployment
13. Monitoring and maintenance

Stabilize the existing search-to-export pipeline before
introducing frontend development, concurrent scraping,
or browser automation.

## 6. Architecture Standards

Maintain separation of concerns.

Keep responsibilities separated between:

- Search providers
- Data models
- Data mapping
- Contact extraction
- Website scraping
- Business services
- Deduplication
- Lead scoring
- Exporters
- Security utilities
- Persistence
- API endpoints
- Background workers
- User interface

Avoid circular dependencies.

Use dependency injection where appropriate to improve
testability and reduce unnecessary coupling.

Keep business logic independent of external providers
and presentation layers whenever practical.

## 7. Python Standards

- Use clear and descriptive names.
- Follow consistent Python naming conventions.
- Use type hints where appropriate.
- Keep functions focused on a single responsibility.
- Avoid unnecessary global state.
- Avoid mutable default arguments.
- Handle exceptions intentionally.
- Do not silently suppress unexpected errors.
- Use context managers for managed resources when appropriate.
- Write docstrings for non-obvious public interfaces.
- Follow the existing project formatting conventions.

Use Ruff for linting and formatting.

## 8. Testing Standards

Use pytest for automated testing.

Every meaningful new feature must include appropriate tests.

Every confirmed bug should have a regression test where possible.

Tests should cover:

- Normal behavior
- Boundary conditions
- Invalid input
- Missing data
- External service failures
- Malformed responses
- Retry behavior
- Security-related behavior
- Previously discovered bugs

Mock external services during ordinary automated tests.

Automated tests must not consume paid Serper API credits.

Tests must not require production credentials.

Never remove or weaken a valid test merely to make
the test suite pass.

## 9. Verification Commands

Run the following commands before declaring significant
backend changes complete:

    python -m pytest
    python -m ruff check .
    python -m ruff format --check .

GitHub Actions must pass before a pushed checkpoint is
considered fully verified.

Warnings should be investigated and documented when
they cannot be immediately resolved.

## 10. Security Standards

Never commit:

- API keys
- Passwords
- Access tokens
- Production credentials
- Private configuration files
- Sensitive customer or business data

Use environment variables for secrets.

Maintain a safe .env.example file.

Treat external websites and external API responses
as untrusted input.

Protect against:

- Server-side request forgery (SSRF)
- Unsafe redirects
- DNS rebinding
- Excessive response sizes
- Unbounded network requests
- Malformed external responses
- CSV and Excel formula injection
- SQL injection
- Unauthorized application access
- Resource exhaustion

Do not disable security controls merely to make
a website or external service accessible.

## 11. External API Standards

External API integrations must include appropriate:

- Request timeouts
- Rate limiting
- Retry policies
- Response validation
- Error handling
- Resource cleanup
- Usage and cost controls

Avoid infinite retries.

Do not retry permanent failures unnecessarily.

Preserve provider usage limits.

Do not perform unnecessary paid API requests.

## 12. Website Discovery and Scraping

Prefer official business websites.

Avoid treating unrelated directories, articles,
and third-party listings as official business websites.

Respect applicable laws, website terms, privacy requirements,
and relevant access restrictions.

Collect only business information necessary for the
platform's legitimate purpose.

Do not bypass authentication, access controls, or CAPTCHA.

Validate URLs and redirects before making network requests.

Individual website failures should not unnecessarily
terminate an entire business discovery job.

Maintain extraction status and useful failure information.

## 13. Data Quality Standards

Business information must be validated, normalized,
and deduplicated where possible.

Support international:

- Country codes
- Phone numbers
- Addresses
- Business categories
- Website domains
- Character encodings

Do not assume all businesses are located in Nepal.

Do not invent missing business information.

Missing and invalid data must be represented explicitly.

Retain source information where appropriate.

Lead quality must not be confused with independently
verified business legitimacy.

## 14. Documentation Standards

The repository is the permanent source of truth.

Maintain the following documentation:

- README.md
- AGENTS.md
- docs/PROJECT_CONTEXT.md
- docs/REQUIREMENTS.md
- docs/ARCHITECTURE.md
- docs/ROADMAP.md
- docs/PROJECT_STATUS.md
- docs/DECISIONS.md
- docs/BACKEND_AUDIT.md
- docs/DEVELOPMENT_LOG.md

Update relevant documentation when requirements,
architecture, implementation, or project status changes.

Keep completed, in-progress, blocked, and pending tasks
clearly distinguishable.

Documentation must reflect verified implementation
rather than planned features being presented as completed.

## 15. Git and Version Control

Use small, meaningful commits.

Write descriptive commit messages.

Review changes before committing.

Do not commit unrelated modifications together unnecessarily.

Do not perform destructive Git operations without
explicit approval.

Do not overwrite existing user changes.

Do not push unverified implementation changes.

Follow the repository's established branching workflow.

## 16. Technical Debt Management

Record known weaknesses and deferred improvements.

Classify issues according to their impact and severity.

Prioritize security vulnerabilities, data corruption,
and reliability problems before cosmetic improvements.

Do not hide known defects from project maintainers.

Document the reason when an issue is intentionally deferred.

## 17. Definition of Done

A task is complete when:

- Its requirements are satisfied.
- Relevant implementation has been reviewed.
- Appropriate tests have been added or updated.
- Required tests pass.
- Ruff checks pass where applicable.
- Security implications have been considered.
- Relevant documentation is updated.
- Changes are committed when appropriate.
- Remote CI passes when changes are pushed.

## 18. Mentoring Rules

The developer is actively learning software engineering.

Assistants should:

- Explain why a change is necessary.
- Explain important concepts in understandable language.
- Guide implementation one task at a time.
- Provide complete code when requested.
- Identify mistakes and explain their consequences.
- Encourage understanding rather than blind copying.
- Maintain continuity using repository documentation.

Do not overwhelm the developer with multiple unrelated
implementation tasks at once.

## 19. Project Continuation Protocol

When beginning a new development session:

1. Read AGENTS.md.
2. Read the current project status.
3. Read the master roadmap.
4. Review the relevant development log.
5. Inspect the current Git state.
6. Identify the next unfinished task.
7. Verify relevant implementation before modifying it.

If documentation and implementation disagree,
investigate and reconcile the discrepancy.

Do not assume conversation memory is authoritative
when repository evidence is available.
