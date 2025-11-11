# UHC/Availity Loop Hierarchy Verification Submission Package

## Package Contents

This package contains all materials needed to verify loop hierarchy behavior with UHC Community & State and Availity clearinghouse.

### 1. Technical Analysis
**File**: `LOOP_HIERARCHY_ANALYSIS.md`
- Comprehensive analysis of the ambiguity issue
- X12 005010X222A1 loop structure documentation
- Specific questions for UHC/Availity
- 3 detailed scenarios with EDI structure examples

### 2. Test Scenarios
**Directory**: `test_scenarios/`
- 3 JSON input files with complete claim data
- 3 EDI output files ready for staging submission
- Compliance analysis script
- Comprehensive README with submission instructions

### 3. This Submission Package
**File**: `UHC_AVAILITY_SUBMISSION_PACKAGE.md` (this file)
- Contact information and submission channels
- Pre-written email templates
- Submission tracking checklist
- Response documentation template

---

## Submission Channels

### UHC Community & State

**Organization**: UnitedHealth Community & State
**Payer ID**: 87726
**Product**: UHC Kentucky Medicaid Managed Care

**EDI Technical Support**:
- **Portal**: UHC Provider Portal → EDI Support
- **Email**: [TBD - Check UHC provider portal for current contact]
- **Phone**: [TBD - Check UHC provider portal]
- **Hours**: Monday-Friday, 8:00 AM - 5:00 PM ET

**Staging Environment**:
- **Access**: UHC EDI Test/Staging Portal
- **Credentials**: [Provider organization credentials]
- **Submission Method**: Direct EDI upload or clearinghouse test mode

**Documentation**:
- UHC Community & State Provider Manual
- UHC EDI Companion Guide for 837P
- URL: https://www.uhccommunityplan.com/ky/providers.html

---

### Availity Clearinghouse

**Organization**: Availity, LLC
**Clearinghouse ID**: 030240928

**Technical Support**:
- **Portal**: Availity Essentials → Support
- **Email**: clientservices@availity.com
- **Phone**: 1-800-AVAILITY (1-800-282-4548)
- **Hours**: 24/7 Technical Support

**Staging/Test Environment**:
- **Access**: Availity Test Account (separate from production)
- **Test Payer ID**: Use UHC test payer ID or production ID in test mode
- **Submission Method**: Availity web portal or API

**Documentation**:
- Availity EDI Implementation Guide
- X12 837P Professional Claims Guide
- URL: https://www.availity.com/support

---

## Email Templates

### Template 1: UHC Community & State Technical Inquiry

**Subject**: X12 837P Loop Hierarchy Verification - NEMT Ambulance Pickup/Dropoff (Payer ID: 87726)

**To**: [UHC EDI Technical Support Email]
**CC**: [Your organization's EDI team]
**Priority**: High
**Reference**: Loop 2310E/F vs 2420G/H Ambiguity

**Email Body**:

```
Dear UHC Community & State EDI Technical Support,

We are implementing NEMT 837P professional claims submission for UHC Kentucky Medicaid
(Payer ID: 87726) and require technical clarification on X12 loop hierarchy for
ambulance pickup/dropoff locations.

ISSUE SUMMARY:
We have identified an ambiguity in the ANSI X12 005010X222A1 specification regarding
ambulance pickup and dropoff locations:

- Loop 2310E (claim-level pickup) uses NM1*PW qualifier
- Loop 2420G (service-level pickup) uses NM1*PW qualifier (IDENTICAL)
- Loop 2310F (claim-level dropoff) uses NM1*45 qualifier
- Loop 2420H (service-level dropoff) uses NM1*45 qualifier (IDENTICAL)

When both claim-level AND service-level locations are present in a single claim, the
identical NM1 qualifiers create parsing ambiguity.

SPECIFIC QUESTIONS:

1. PRECEDENCE: When both claim-level (2310E/F) and service-level (2420G/H) pickup/dropoff
   locations are present, which level takes precedence for adjudication?
   - Does service-level override claim-level?
   - Is claim-level used only when service-level is absent?
   - Are both levels processed independently?

2. RECOMMENDED APPROACH: For NEMT claims with multiple service lines (e.g., A0130 outbound
   + A0200 return), which structure is preferred:
   a) Service-level only (Loop 2420G/H) - Each service specifies its own locations
   b) Claim-level only (Loop 2310E/F) - Default locations apply to all services
   c) Mixed approach - Claim defaults with service-level overrides when different

3. QUALIFIER USAGE: Are the identical NM1 qualifiers (PW/45) acceptable at both levels,
   or should we use alternative qualifiers at the claim level (e.g., NM1*TL)?

4. VALIDATION: Will claims with both claim-level AND service-level locations pass UHC
   front-end validation, or will they be rejected as malformed?

TEST SCENARIOS PROVIDED:

We have prepared three test EDI files demonstrating each approach:

1. scenario1_service_level_only.edi (Claim: SCENARIO1-001)
   - Uses 2420G/H only for pickup/dropoff at each service line
   - No claim-level pickup/dropoff (2310E/F)
   - Clean, unambiguous structure

2. scenario2_claim_level_only.edi (Claim: SCENARIO2-001)
   - Uses 2310E/F only for pickup/dropoff at claim level
   - No service-level pickup/dropoff (2420G/H)
   - Alternative approach with shared locations

3. scenario3_both_levels_ambiguous.edi (Claim: SCENARIO3-AMBIGUOUS)
   - Uses BOTH 2310E/F (claim) AND 2420G/H (service)
   - Demonstrates the ambiguity with identical qualifiers
   - Critical test case requiring verification

ATTACHMENTS:
- LOOP_HIERARCHY_ANALYSIS.md - Detailed technical analysis
- scenario1_service_level_only.edi - Test claim #1
- scenario2_claim_level_only.edi - Test claim #2
- scenario3_both_levels_ambiguous.edi - Test claim #3
- test_scenarios/README.md - Comprehensive documentation

REQUESTED ACTIONS:

1. Clarify the precedence rules and recommended approach for NEMT claims
2. Confirm whether Scenario 3 (both levels present) is acceptable or will be rejected
3. Provide any UHC-specific requirements or preferences for loop hierarchy
4. If possible, test the attached scenarios in UHC staging environment and share results

CONTACT INFORMATION:
[Your Name]
[Your Title]
[Organization Name]
[Email Address]
[Phone Number]

We appreciate your assistance in resolving this ambiguity before our production go-live.
Please let us know if you need any additional information.

Thank you,
[Your Name]
[Your Organization]
```

---

### Template 2: Availity Clearinghouse Technical Inquiry

**Subject**: X12 837P Loop Hierarchy - Ambulance Pickup/Dropoff Locations (Receiver ID: 030240928)

**To**: clientservices@availity.com
**CC**: [Your organization's EDI team]
**Priority**: High
**Reference**: Loop 2310E/F vs 2420G/H Parsing

**Email Body**:

```
Dear Availity Technical Support,

We are submitting NEMT 837P professional claims through Availity (Receiver ID: 030240928)
to UHC Community & State (Payer ID: 87726) and need clarification on how Availity
processes loop hierarchy for ambulance pickup/dropoff locations.

ISSUE SUMMARY:
The X12 837P specification allows ambulance pickup/dropoff locations at TWO different levels:
- Claim level: Loop 2310E (pickup) / 2310F (dropoff)
- Service level: Loop 2420G (pickup) / 2420H (dropoff)

Both levels use IDENTICAL NM1 qualifiers (PW for pickup, 45 for dropoff), creating
potential parsing ambiguity when both are present.

SPECIFIC QUESTIONS FOR AVAILITY:

1. PARSING BEHAVIOR: How does Availity's X12 parser distinguish between claim-level
   (2310E/F) and service-level (2420G/H) pickup/dropoff when both use identical qualifiers?
   - Does Availity rely on segment positioning (before vs after LX)?
   - Are there any validation rules that reject claims with both levels present?

2. CLEARINGHOUSE VALIDATION: Will Availity accept and forward claims that include
   pickup/dropoff at BOTH claim and service levels, or will this fail validation?

3. PAYER-SPECIFIC RULES: Does Availity have any UHC-specific translation rules that
   affect how pickup/dropoff locations are processed or transformed before forwarding?

4. RECOMMENDED APPROACH: What is Availity's recommendation for NEMT claims with multiple
   service lines - use claim-level only, service-level only, or both?

TEST SCENARIOS PROVIDED:

We have prepared three test EDI files to validate Availity's processing:

1. scenario1_service_level_only.edi
   - Pickup/dropoff at service level (2420G/H) only
   - Expected: Pass validation and forward to payer

2. scenario2_claim_level_only.edi
   - Pickup/dropoff at claim level (2310E/F) only
   - Expected: Pass validation and forward to payer

3. scenario3_both_levels_ambiguous.edi
   - Pickup/dropoff at BOTH claim and service levels
   - Expected: Pass or Fail? (critical test case)

REQUESTED ACTIONS:

1. Confirm Availity's parsing logic for duplicate NM1 qualifiers at different loop levels
2. Test the attached scenarios in Availity staging/test environment
3. Share validation results and any error/warning messages generated
4. Provide guidance on recommended approach for production claims

TESTING ENVIRONMENT:
We are prepared to submit these test scenarios through:
- Availity web portal (test account)
- Availity API (test credentials)
- Direct EDI file upload

Please advise on the preferred testing method and any setup requirements.

ATTACHMENTS:
- LOOP_HIERARCHY_ANALYSIS.md - Technical analysis
- Three test EDI files (scenarios 1-3)
- test_scenarios/README.md - Documentation

CONTACT INFORMATION:
[Your Name]
[Your Title]
[Organization Name]
[Email Address]
[Phone Number]
[Availity Organization ID]

We would appreciate a response within 5-7 business days if possible, as this is blocking
our production deployment. Please let us know if you need additional information.

Thank you for your assistance,
[Your Name]
[Your Organization]
```

---

## Submission Tracking Checklist

### Pre-Submission
- [ ] Review LOOP_HIERARCHY_ANALYSIS.md for completeness
- [ ] Verify all 3 test scenario EDI files are generated and valid
- [ ] Run Agent 2 compliance checks on all scenarios
- [ ] Collect organization credentials and contact information
- [ ] Identify internal stakeholders for CC on emails

### UHC Community & State Submission
- [ ] Locate current UHC EDI technical support contact information
- [ ] Customize email template with organization details
- [ ] Attach all required files (analysis + 3 EDI scenarios + README)
- [ ] Send email inquiry to UHC EDI support
- [ ] **Date Sent**: ______________
- [ ] **Ticket/Reference Number**: ______________
- [ ] Submit test scenarios to UHC staging environment (if access available)
- [ ] **Staging Submission Date**: ______________
- [ ] **Staging Confirmation Numbers**:
  - Scenario 1: ______________
  - Scenario 2: ______________
  - Scenario 3: ______________

### Availity Clearinghouse Submission
- [ ] Verify Availity test account access and credentials
- [ ] Customize email template with organization details
- [ ] Attach all required files
- [ ] Send email inquiry to Availity technical support
- [ ] **Date Sent**: ______________
- [ ] **Ticket/Reference Number**: ______________
- [ ] Submit test scenarios through Availity staging
- [ ] **Staging Submission Date**: ______________
- [ ] **Availity Transaction IDs**:
  - Scenario 1: ______________
  - Scenario 2: ______________
  - Scenario 3: ______________

### Response Tracking
- [ ] Document UHC response received
  - **Date**: ______________
  - **Respondent**: ______________
  - **Summary**: ______________
- [ ] Document Availity response received
  - **Date**: ______________
  - **Respondent**: ______________
  - **Summary**: ______________
- [ ] Document staging test results (acceptance/rejection)
- [ ] Document any 277CA acknowledgments received
- [ ] Document any rejection codes or error messages

### Follow-Up Actions
- [ ] Update LOOP_HIERARCHY_ANALYSIS.md with verified findings
- [ ] Create LOOP_HIERARCHY_RESOLUTION.md with final recommendation
- [ ] Implement fixes in builder.py based on guidance
- [ ] Add regression tests for verified scenarios
- [ ] Update README.md with best practices
- [ ] Complete Sprint 1.5 final tasks

---

## Response Documentation Template

### UHC Response Summary

**Date Received**: ______________
**Respondent Name/Title**: ______________
**Ticket/Reference**: ______________

**Question 1 - Precedence Rules**:
- Answer: ______________
- Notes: ______________

**Question 2 - Recommended Approach**:
- Answer: ______________
- Preferred method: ☐ Service-level only ☐ Claim-level only ☐ Both acceptable
- Notes: ______________

**Question 3 - Qualifier Usage**:
- Answer: ______________
- Alternative qualifiers required: ☐ Yes ☐ No
- Notes: ______________

**Question 4 - Validation Behavior**:
- Answer: ______________
- Scenario 3 acceptance: ☐ Accepted ☐ Rejected
- Notes: ______________

**Staging Test Results**:
- Scenario 1: ☐ Accepted ☐ Rejected - Code: ______________
- Scenario 2: ☐ Accepted ☐ Rejected - Code: ______________
- Scenario 3: ☐ Accepted ☐ Rejected - Code: ______________

**Additional Guidance**: ______________

---

### Availity Response Summary

**Date Received**: ______________
**Respondent Name/Title**: ______________
**Ticket/Reference**: ______________

**Question 1 - Parsing Behavior**:
- Answer: ______________
- Uses segment positioning: ☐ Yes ☐ No
- Notes: ______________

**Question 2 - Clearinghouse Validation**:
- Answer: ______________
- Scenario 3 processing: ☐ Forwards to payer ☐ Rejects ☐ Warning only
- Notes: ______________

**Question 3 - Payer-Specific Rules**:
- Answer: ______________
- UHC translation rules: ☐ Yes ☐ No
- Notes: ______________

**Question 4 - Recommended Approach**:
- Answer: ______________
- Recommendation: ______________

**Staging Test Results**:
- Scenario 1: ☐ Forwarded ☐ Rejected - Code: ______________
- Scenario 2: ☐ Forwarded ☐ Rejected - Code: ______________
- Scenario 3: ☐ Forwarded ☐ Rejected - Code: ______________

**Additional Guidance**: ______________

---

## Timeline Expectations

- **Email Response**: 5-7 business days typical
- **Staging Results**: 1-3 days after submission
- **277CA Acknowledgments**: 1-2 days after payer receipt
- **Total Resolution Time**: 2-3 weeks estimated

---

## Escalation Path

If no response within 10 business days:

### UHC Escalation:
1. Contact UHC provider relations representative
2. Request escalation to EDI technical team
3. Reference original inquiry ticket number
4. Request priority handling as production blocker

### Availity Escalation:
1. Call Availity support hotline: 1-800-AVAILITY
2. Request supervisor/technical specialist
3. Reference email ticket number
4. Escalate as production implementation blocker

---

## Success Criteria

Sprint 1.5 is considered complete when:
1. ✅ Test scenarios created and validated
2. ⏳ UHC response received with clear guidance
3. ⏳ Availity response received with parsing confirmation
4. ⏳ At least one scenario confirmed acceptable in staging
5. ⏳ Implementation plan documented for fixes
6. ⏳ Code changes committed (if required)

---

**Package Created**: 2025-11-11
**Status**: Ready for Submission
**Priority**: Critical (P0) - Production Blocker
**Estimated Resolution**: 2-3 weeks from submission
