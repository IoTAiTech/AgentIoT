# SPDX-License-Identifier: MIT
# Version: 0.157.1 | Date: 2026-08-11

Feature: Approval-gated private network discovery
  Scenario: A bounded scan does not mutate Asset Inventory
    Given an authenticated operator explicitly authorizes a private IPv4 scan
    When the dashboard checks the fixed protocol-hint ports
    Then it reads no service payload or credential
    And each observation remains a temporary approval candidate
    And Asset Inventory and telemetry remain unchanged

  Scenario: The operator promotes one selected observation
    Given a queued observation with a current evidence fingerprint
    When an authorized operator confirms its asset mapping
    Then one asset and one device are created atomically
    And approved protocol hints appear in the CMDB graph
    And no synthetic telemetry is created

  Scenario: Unsafe or stale discovery is rejected
    Given a public, special, oversized, expired, or changed discovery target
    When discovery or approval is requested
    Then the request is rejected without inventory mutation
