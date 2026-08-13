Feature: CMDB auto-discovery from hardware evidence

  Scenario: Happy path
    Given a simulator run writes registered sensors through the hardware data interface
    When the operator opens the CI/CMDB configuration-items view
    Then the dashboard shows sensor CIs with profile, protocol, standard, and USB evidence

  Scenario: Edge case
    Given a registered device has telemetry but no matching hardware profile evidence
    When the CMDB builds configuration items
    Then the device remains a generic device CI and is not counted as an auto-discovered sensor

  Scenario: Failure case
    Given telemetry uses a known sensor metric without matching configuration-profile evidence
    When the CMDB evaluates the device
    Then metric-only spoofing is rejected and no sensor standards or USB support are claimed
