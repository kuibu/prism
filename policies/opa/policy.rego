package prism

# Iteration 1 baseline policy. Full grant/revoke flow is introduced in Iteration 3.
default allow := {
  "allow": false,
  "reason": "no_matching_policy"
}

allow := {
  "allow": true,
  "reason": "healthcheck"
} if {
  input.action == "healthcheck"
}
