# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

Feature: Hardware discovery profile ingestion

  Scenario: Happy path
    Given an operator submits a USB sensor profile with matching protocol and standard evidence
    When the hardware discovery profile is accepted
    Then the asset, device, configuration profile, telemetry record, and CMDB sensor CI are available

  Scenario: Edge case
    Given the hardware profile uses a human-readable Raspberry Pi board label
    When the firmware compatibility normalizer maps it to a canonical board id
    Then the profile can be validated against the supported hardware catalog

  Scenario: USB descriptor evidence
    Given a discovered USB sensor reports VID, PID, class, interface class, driver, vendor, product, and standard descriptor evidence
    When the descriptor matches the approved hardware profile rules
    Then the CMDB records only sanitized descriptor evidence and redacts serial identifiers

  Scenario: USB sysfs edge preview
    Given an edge gateway reads USB descriptor evidence from Linux sysfs
    When the optional USB discovery plugin previews matched hardware profiles
    Then the operator receives a sanitized registration payload for CMDB auto-discovery

  Scenario: Failure case
    Given a discovered device reports a known metric without matching standard evidence
    When the operator submits the hardware profile
    Then the request is rejected and no CMDB CI is created from untrusted evidence
