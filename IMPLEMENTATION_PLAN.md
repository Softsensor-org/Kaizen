# Implementation Plan: Complete Agent Architecture & Critical Fixes

## Executive Summary

**Objective:** Complete the agent architecture designed in agents.md and fix critical X12 compliance bugs to achieve production readiness.

**Timeline:** 8 days (64 hours)
**Current Status:** 60% complete - P0/P1/P2 done, but missing core agents
**Target:** 100% production-ready with full agent architecture

---

## Critical Gaps Identified

### **Architectural Gaps (from agents.md)**
1. ❌ **Agent 1: Pre-Submission Validator** - Only 30% complete, no structured reports
2. ❌ **Agent 2: X12 Compliance Checker** - 0% complete, no EDI validation
3. ❌ **Agent 3: UHC Business Rule Validator** - 0% complete, no payer validation
4. ⚠️ **Agent 4: Claim Enrichment** - 60% complete, missing timestamps/control numbers
5. ❌ **Agent 5: Batch Processor** - 0% complete, no multi-claim support

### **Critical X12 Bugs (from gap analysis)**
1. ❌ **K3 Segment Ordering** - Line-level K3 appears AFTER SVD/CAS (should be before)
2. ❌ **SV1 Emergency Indicator** - At wrong element position (SV110 vs SV111)
3. ❌ **Loop Hierarchy Ambiguity** - Identical NM1 qualifiers at 2310 and 2420 levels
4. ❌ **Missing Loop Markers** - No comments indicating loop boundaries

---

## Sprint Breakdown

### **Sprint 1: Critical Fixes + Foundation (2 days - 16 hours)**

**Goal:** Eliminate critical X12 bugs and implement EDI validation safety net

#### **Tasks:**

**1.1 Fix K3 Segment Ordering Bug** ⏱️ 1 hour
- **File:** `nemt_837p_converter/builder.py`
- **Current Line:** 410
- **Issue:** K3*PYMS after SVD/CAS
- **Fix:** Move line 410 before line 391 (provider loops)
- **Test:** Verify K3 appears before NM1*DQ in generated EDI
- **Success Criteria:** K3 segment appears in correct position in all test cases

**1.2 Fix SV1 Emergency Indicator Position** ⏱️ 1 hour
- **File:** `nemt_837p_converter/builder.py`
- **Current Line:** 360
- **Issue:** Emergency indicator at SV110 (should be SV111)
- **Fix:** Adjust SV1 segment construction
- **Test:** Generate EDI with emergency=True, verify position
- **Success Criteria:** Emergency indicator in SV111 position

**1.3 Add Loop Marker Comments** ⏱️ 2 hours
- **File:** `nemt_837p_converter/builder.py`
- **Issue:** No loop boundaries documented in code
- **Fix:** Add comments like `# Loop 2010AA - Billing Provider`, `# Loop 2310E - Ambulance Pickup`
- **Locations:**
  - Line 264: `# Loop 2010AA - Billing Provider Name`
  - Line 276: `# Loop 2010BA - Subscriber Name`
  - Line 288: `# Loop 2300 - Claim Information`
  - Line 351: `# Loop 2310D - Rendering Provider (Supervising)`
  - Line 344: `# Loop 2310E - Ambulance Pick-Up Location`
  - Line 347: `# Loop 2310F - Ambulance Drop-Off Location`
  - Line 358: `# Loop 2400 - Service Line Number`
  - Line 391: `# Loop 2420D - Service Facility Supervising Provider`
  - Line 402: `# Loop 2420G - Service Facility Ambulance Pick-Up`
  - Line 405: `# Loop 2420H - Service Facility Ambulance Drop-Off`
  - Line 413: `# Loop 2430 - Line Adjudication Information`
- **Success Criteria:** All loop boundaries clearly marked

**1.4 Verify Loop Hierarchy with UHC** ⏱️ 2 hours
- **Action:** Contact UHC/Availity technical support
- **Questions:**
  1. Are both 2310E/F (claim-level) AND 2420G/H (service-level) pickup/dropoff required?
  2. If both required, how should they be differentiated? (different qualifiers? REF segments?)
  3. Is our custom NTE/K3 format documented in UHC companion guide?
- **Document:** Save response in `docs/UHC_VERIFICATION.md`
- **Success Criteria:** Clear answer on loop requirements

**1.5 Fix Loop Hierarchy Based on UHC Response** ⏱️ 2 hours
- **File:** `nemt_837p_converter/builder.py`
- **Depends on:** Task 1.4 response
- **Options:**
  - Option A: If only one level needed, remove duplicate
  - Option B: If both needed, add REF segments or change qualifiers to differentiate
  - Option C: Add loop positioning logic
- **Success Criteria:** Loop hierarchy compliant with UHC requirements

**1.6 Implement Agent 2: X12 Compliance Checker** ⏱️ 8 hours
- **New File:** `nemt_837p_converter/validators/x12_checker.py`
- **Purpose:** Validate generated EDI against X12 spec
- **Features:**
  - Parse EDI into segments
  - Validate ISA/GS/ST/SE/GE/IEA structure
  - Check segment counts (SE, GE, IEA)
  - Validate control numbers match
  - Check required segments present
  - Validate loop hierarchy
  - Return ComplianceReport
- **Integration:** Add to build pipeline (optional flag)
- **Tests:** `tests/test_x12_checker.py`
- **Success Criteria:** Can detect common EDI errors

---

### **Sprint 2: Validation Architecture (2 days - 16 hours)**

**Goal:** Complete validation agent architecture with structured reporting

#### **Tasks:**

**2.1 Refactor to Agent 1: Pre-Submission Validator** ⏱️ 4 hours
- **New File:** `nemt_837p_converter/validators/pre_submission.py`
- **Current:** `validate_claim_json()` in builder.py returns single error string
- **Refactor to:**
  ```python
  class ValidationReport:
      errors: List[ValidationError]
      warnings: List[ValidationWarning]
      info: List[ValidationInfo]
      is_valid: bool

      def to_json(self) -> dict
      def to_text(self) -> str
      def to_table(self) -> str

  class PreSubmissionValidator:
      def validate(self, claim_json: dict) -> ValidationReport
  ```
- **Features:**
  - NPI checksum validation (Luhn algorithm)
  - Cross-field business rules
  - Structured error reporting
  - Warning vs error distinction
- **Migration:** Update builder.py to use new validator
- **Tests:** `tests/test_pre_submission_validator.py`
- **Success Criteria:** Structured reports with field-level errors

**2.2 Add Loop Hierarchy Tests** ⏱️ 4 hours
- **File:** `tests/test_loop_hierarchy.py`
- **Tests:**
  - `test_2310_before_2400()` - Claim loops before service loops
  - `test_2420_within_2400()` - Service loops within LX boundaries
  - `test_provider_loop_order()` - Provider loops in correct sequence
  - `test_no_orphan_segments()` - All segments within proper loops
  - `test_loop_markers_present()` - Verify comment markers exist
- **Success Criteria:** Can detect loop positioning violations

**2.3 Implement Agent 3: UHC Business Rule Validator** ⏱️ 6 hours
- **New File:** `nemt_837p_converter/validators/uhc_rules.py`
- **Purpose:** Validate UHC-specific requirements
- **Features:**
  - K3 segment format validation (PYMS-P/D, SUB-xxx, SNWK-I/O, TRPN-ASPUFEELEC/PAPER)
  - NTE group structure validation (GRP-xxx;SGR-xxx;CLS-xxx;PLN-xxx;PRD-xxx)
  - CR1 ambulance data validation
  - REF*LU trip number presence validation
  - NTE location/time format validation (PULOC-xx;PUTIME-xxxx)
  - Trip details format validation (TRIPNUM-xxxxxxxxx;SPECNEED-Y/N)
  - Return UHCReport with violations
- **Tests:** `tests/test_uhc_validator.py`
- **Success Criteria:** Can catch UHC-specific format errors

**2.4 Add Comprehensive Agent Tests** ⏱️ 2 hours
- **Files:**
  - `tests/test_validation_pipeline.py` - Test agent chaining
  - `tests/test_validation_reports.py` - Test report formats
- **Tests:**
  - `test_agent_pipeline()` - Agent 1 → Agent 2 → Agent 3
  - `test_error_aggregation()` - Multiple agents, single report
  - `test_json_report_format()` - JSON serialization
  - `test_text_report_format()` - Human-readable output
- **Success Criteria:** All agents work together seamlessly

---

### **Sprint 3: Production Readiness (3 days - 24 hours)**

**Goal:** Add batch processing, logging, and production features

#### **Tasks:**

**3.1 Implement Agent 5: Batch Processor** ⏱️ 8 hours
- **New File:** `nemt_837p_converter/batch.py`
- **Features:**
  ```python
  class BatchProcessor:
      def process_batch(self, claims: List[dict]) -> BatchResult:
          # Single ISA/GS envelope
          # Multiple ST/SE sets (one per claim)
          # Error handling (skip invalid, continue)
          # Summary report

  class BatchResult:
      edi_content: str
      successful: List[ClaimResult]
      failed: List[ClaimResult]
      summary: BatchSummary
  ```
- **Batch JSON Format:**
  ```json
  {
    "batch_id": "BATCH-2025-001",
    "claims": [
      { /* claim 1 */ },
      { /* claim 2 */ }
    ]
  }
  ```
- **Control Numbers:** Manage ISA/GS/ST across batch
- **CLI:** Add `--batch` flag
- **Tests:** `tests/test_batch_processor.py`
- **Success Criteria:** Can process 100+ claims in single file

**3.2 Add Logging/Monitoring** ⏱️ 4 hours
- **File:** `nemt_837p_converter/logging_config.py`
- **Features:**
  - Structured JSON logging
  - Log levels (DEBUG, INFO, WARNING, ERROR)
  - Correlation IDs (claim_number)
  - Performance metrics (timing)
  - Integration with all agents
- **Usage:**
  ```python
  logger.info("Building 837P", extra={
      "correlation_id": claim_number,
      "claim_count": 1,
      "payer": "UHC_CS"
  })
  ```
- **Output:** Can send to stdout, file, or monitoring service
- **Success Criteria:** All operations logged with correlation IDs

**3.3 Add Performance Tests** ⏱️ 4 hours
- **File:** `tests/test_performance.py`
- **Tests:**
  - `test_single_claim_performance()` - < 100ms
  - `test_large_claim_100_services()` - < 500ms
  - `test_batch_100_claims()` - < 10s
  - `test_batch_1000_claims()` - < 60s
  - `test_memory_usage_batch()` - < 100MB for 1000 claims
- **Tools:** pytest-benchmark
- **Success Criteria:** Meets performance targets

**3.4 Complete Agent 4: Enrichment** ⏱️ 2 hours
- **File:** `nemt_837p_converter/enrichment.py`
- **Add Missing Features:**
  - Timestamp generation (if missing)
  - Control number generation option
  - Provider registry lookup (optional)
  - Usage indicator defaulting
- **New Methods:**
  ```python
  def add_timestamps(self, claim_json: dict) -> dict:
      # Add current timestamp to BHT, DTP if missing

  def generate_control_numbers(self, claim_json: dict, cn: ControlNumbers) -> dict:
      # Add ISA/GS/ST control numbers
  ```
- **Success Criteria:** All features from agents.md implemented

**3.5 Create JSON Schema File** ⏱️ 4 hours
- **New File:** `schema/claim.schema.json`
- **Purpose:** Formal JSON schema for external validation
- **Include:**
  - All required fields
  - Field types and formats
  - String length limits
  - Enum values for code fields
  - Nested object structures
- **Validation:** Can use jsonschema library
- **Documentation:** Link from README
- **Success Criteria:** Example claim validates against schema

**3.6 Add Batch Processor Tests** ⏱️ 2 hours
- **File:** `tests/test_batch_processor.py`
- **Tests:**
  - `test_batch_10_claims()` - Small batch
  - `test_batch_100_claims()` - Medium batch
  - `test_batch_with_failures()` - Error handling
  - `test_batch_control_numbers()` - Sequential numbering
  - `test_batch_summary_report()` - Summary accuracy
- **Success Criteria:** All batch scenarios covered

---

### **Sprint 4: Documentation & Polish (1 day - 8 hours)**

**Goal:** Complete documentation and final test coverage

#### **Tasks:**

**4.1 Field Mapping Documentation** ⏱️ 4 hours
- **New File:** `docs/FIELD_MAPPING.md`
- **Content:** Complete JSON → X12 mapping table
- **Format:**
  ```markdown
  | JSON Path | X12 Segment | Loop | Element | Required | Max Length | Notes |
  |-----------|-------------|------|---------|----------|------------|-------|
  | billing_provider.npi | NM1 | 2010AA | NM109 | Yes | 10 | Must be 10 digits |
  | claim.clm_number | CLM | 2300 | CLM01 | Yes | 30 | Unique identifier |
  ```
- **Include:** All ~100 supported fields
- **Success Criteria:** Complete reference for developers

**4.2 Update README with Agent Workflow** ⏱️ 2 hours
- **File:** `README.md`
- **Add Sections:**
  - Agent Architecture overview
  - Validation workflow diagram
  - Agent usage examples
  - Batch processing guide
- **Update:** Installation, testing, troubleshooting sections
- **Success Criteria:** Clear explanation of agent architecture

**4.3 Segment Ordering Tests** ⏱️ 2 hours
- **File:** `tests/test_segment_ordering.py`
- **Tests:**
  - `test_2300_segment_order()` - CLM before DTP before HI before REF
  - `test_2400_segment_order()` - LX before SV1 before DTP before NTE
  - `test_provider_segment_order()` - NM1 before N3 before N4 before REF
  - `test_envelope_order()` - ISA → GS → ST → ... → SE → GE → IEA
- **Success Criteria:** Segment order verified for all loops

---

## File Structure After Completion

```
nemt_837p_converter/
├── __init__.py                    # Package exports
├── builder.py                     # EDI builder (updated with loop markers)
├── cli.py                         # CLI (updated with --batch flag)
├── codes.py                       # Code value lookups
├── enrichment.py                  # Agent 4 (completed)
├── payers.py                      # Payer configurations
├── x12.py                         # X12 writer
├── logging_config.py              # NEW: Logging setup
├── batch.py                       # NEW: Agent 5 - Batch Processor
└── validators/                    # NEW: Validator agents
    ├── __init__.py
    ├── pre_submission.py          # NEW: Agent 1
    ├── x12_checker.py             # NEW: Agent 2
    └── uhc_rules.py               # NEW: Agent 3

tests/
├── test_validation.py             # Existing
├── test_enrichment.py             # Existing
├── test_builder.py                # Existing
├── test_pre_submission_validator.py  # NEW
├── test_x12_checker.py            # NEW
├── test_uhc_validator.py          # NEW
├── test_validation_pipeline.py    # NEW
├── test_loop_hierarchy.py         # NEW
├── test_segment_ordering.py       # NEW
├── test_batch_processor.py        # NEW
└── test_performance.py            # NEW

docs/
├── FIELD_MAPPING.md               # NEW
└── UHC_VERIFICATION.md            # NEW

schema/
└── claim.schema.json              # NEW

IMPLEMENTATION_PLAN.md             # This file
FREQUENCY_CODES.md                 # Existing
agents.md                          # Existing
README.md                          # Updated
```

---

## Success Metrics

### **Sprint 1 Success:**
- ✅ All critical X12 bugs fixed
- ✅ Agent 2 (X12 Compliance Checker) operational
- ✅ Loop hierarchy verified with UHC
- ✅ Can validate EDI output before submission

### **Sprint 2 Success:**
- ✅ Agent 1 (Pre-Submission Validator) with structured reports
- ✅ Agent 3 (UHC Business Rule Validator) operational
- ✅ Loop hierarchy tests passing
- ✅ 3-tier validation pipeline working

### **Sprint 3 Success:**
- ✅ Agent 5 (Batch Processor) can handle 1000+ claims
- ✅ Agent 4 (Enrichment) fully complete
- ✅ Structured logging in place
- ✅ Performance benchmarks passing
- ✅ JSON schema file created

### **Sprint 4 Success:**
- ✅ Complete field mapping documentation
- ✅ README updated with agent architecture
- ✅ All segment ordering tests passing
- ✅ 60+ tests total, all passing

---

## Testing Strategy

### **Unit Tests (40+ tests)**
- Each agent tested independently
- Each bug fix has regression test
- Edge cases covered

### **Integration Tests (10+ tests)**
- Agent pipeline (1→2→3)
- Enrichment + validation
- Batch processing end-to-end

### **Performance Tests (5 tests)**
- Single claim
- Large claim (100 services)
- Batch (100, 1000 claims)
- Memory usage

### **Regression Tests (5 tests)**
- agents.md Gap #1 (CR1 format)
- agents.md Gap #2 (trip number cascade)
- K3 ordering bug
- SV1 emergency indicator
- Loop hierarchy

---

## Risk Mitigation

### **Risk 1: UHC Response Delayed**
- **Mitigation:** Proceed with best-practice X12 implementation
- **Fallback:** Use standard 2310E/F only, skip 2420G/H
- **Timeline Impact:** +1 day if major changes needed

### **Risk 2: Agent 2 More Complex Than Estimated**
- **Mitigation:** Start with basic validation, enhance later
- **MVP:** Segment count, control number validation only
- **Timeline Impact:** Complete MVP in 4 hours, defer complex checks

### **Risk 3: Batch Processing Edge Cases**
- **Mitigation:** Focus on happy path first
- **MVP:** All valid claims, defer complex error handling
- **Timeline Impact:** Can ship batch MVP in 6 hours

---

## Dependencies

### **External:**
- UHC/Availity technical support response (Sprint 1)
- No new Python dependencies needed

### **Internal:**
- Sprint 2 depends on Sprint 1 completion
- Sprint 3 can run parallel to Sprint 2
- Sprint 4 depends on Sprints 1-3

---

## Deliverables

### **Sprint 1:**
- ✅ Bug fixes committed
- ✅ Agent 2 implementation
- ✅ UHC verification documented

### **Sprint 2:**
- ✅ Agent 1 and 3 implementations
- ✅ Validation tests
- ✅ Structured report formats

### **Sprint 3:**
- ✅ Agent 5 implementation
- ✅ Logging configuration
- ✅ Performance benchmarks
- ✅ JSON schema

### **Sprint 4:**
- ✅ Complete documentation
- ✅ Final test suite
- ✅ Updated README

---

## Next Steps

1. **Save this plan** to repository
2. **Start Sprint 1, Task 1.1** - Fix K3 ordering bug
3. **Track progress** using todo list
4. **Demo after each sprint** to validate progress
5. **Adjust timeline** if needed based on UHC response

---

## Notes

- This plan assumes single developer, 8 hours/day
- Can be accelerated with parallel work streams
- Each sprint delivers working, testable value
- Can ship MVP after Sprint 2 if needed (validation complete)
- Sprints 3-4 add production scale and polish

---

**Plan Version:** 1.0
**Created:** November 11, 2025
**Last Updated:** November 11, 2025
**Status:** Ready for Execution
