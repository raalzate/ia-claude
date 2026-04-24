# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Declared JSON Schemas Are the Sole Input Contract
  The CLIOutputEnvelope, ReviewFinding, and AnnotationPayload schemas are the only contracts between the CLI, the validator, the mapper, and the Checks API.

  @TS-015 @FR-002 @FR-003 @P2 @contract
  Scenario: CLIOutputEnvelope rejects payloads missing required fields
    Given a candidate payload missing the "findings" field
    When it is validated against "contracts/cli-output-envelope.schema.json"
    Then validation fails

  @TS-016 @FR-003 @P2 @contract
  Scenario Outline: ReviewFinding enforces field-level invariants
    Given a candidate finding where "<field>" is "<bad_value>"
    When it is validated against "contracts/review-finding.schema.json"
    Then validation fails

    Examples:
      | field    | bad_value     |
      | line     | 0             |
      | line     | -1            |
      | severity | critical      |
      | severity | INFO          |
      | id       |               |
      | message  |               |

  @TS-017 @FR-003 @P2 @contract
  Scenario: ReviewFinding accepts a well-formed payload
    Given a candidate finding with id "f-1", file_path "src/a.py", line 12, severity "warning", category "security", and message "SQL injection risk"
    When it is validated against "contracts/review-finding.schema.json"
    Then validation succeeds

  @TS-018 @FR-005 @P2 @contract
  Scenario: AnnotationPayload enforces the Checks API annotation_level enum
    Given a candidate annotation where annotation_level is "error"
    When it is validated against "contracts/annotation-payload.schema.json"
    Then validation fails

  @TS-019 @FR-005 @P2 @contract
  Scenario: AnnotationPayload accepts a well-formed payload
    Given a candidate annotation with path "src/a.py", start_line 12, end_line 12, annotation_level "warning", message "SQL injection risk", title "[security] f-1"
    When it is validated against "contracts/annotation-payload.schema.json"
    Then validation succeeds
