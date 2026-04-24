# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Schema Contract Conformance for Normalized Payloads and Audit Records
  Every artifact crossing a boundary (model context, audit log) conforms to its declared JSON Schema and invariants — no best-effort shapes reach the model or the log.

  Background:
    Given a completed kata run with the PostToolUse hook enabled
    And the audit log at runs/<session-id>/audit.jsonl exists
    And the declared JSON Schemas live under specs/003-posttool-normalize/contracts/

  @TS-030 @FR-002 @FR-006 @SC-002 @US-001 @P1 @contract
  Scenario: Every appended tool-response message validates against NormalizedPayload schema
    When each tool-response message appended to conversation history is validated against contracts/normalized-payload.schema.json
    Then every message passes schema validation
    And every message carries tool_use_id, status, content, parse_status, and notes fields

  @TS-031 @FR-003 @SC-003 @US-001 @P1 @contract
  Scenario: NormalizedPayload status invariant holds across every appended message
    When each appended NormalizedPayload is inspected
    Then whenever status.code equals "unknown" the status.raw field is non-empty
    And whenever status.code is not "unknown" the status.raw field is null

  @TS-032 @FR-004 @SC-002 @US-001 @P1 @validation
  Scenario: No string field in any NormalizedPayload contains legacy markup characters
    When every string value reachable from an appended NormalizedPayload is scanned
    Then no value contains the characters "<", ">", or CDATA sentinels

  @TS-033 @FR-005 @SC-004 @US-002 @P2 @contract
  Scenario: Every audit record validates against the AuditRecord schema
    When each line of audit.jsonl is validated against contracts/audit-record.schema.json
    Then every record passes schema validation
    And every record carries session_id, tool_use_id, raw_bytes_b64, and raw_sha256 fields

  @TS-034 @FR-005 @SC-004 @US-002 @P2 @validation
  Scenario: Audit SHA-256 roundtrips the raw bytes for every record
    When each AuditRecord in audit.jsonl is loaded
    Then sha256 of base64-decoded raw_bytes_b64 equals raw_sha256 for that record
    And the decoded raw bytes equal the source fixture bytes byte-for-byte

  @TS-035 @FR-001 @FR-005 @US-001 @P1 @validation
  Scenario: Exactly one AuditRecord exists per intercepted tool response
    When the audit.jsonl records are grouped by tool_use_id
    Then each tool_use_id appears in exactly one AuditRecord
    And every tool-response message appended to conversation history has a matching tool_use_id in the audit log
