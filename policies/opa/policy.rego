package prism

default allow := {"allow": false, "reason": "no_active_grant"}

allow := {"allow": true, "reason": "healthcheck"} if {
	input.action == "healthcheck"
} else := {"allow": true, "reason": "grant_active"} if {
	active_matching_grant
} else := {"allow": false, "reason": "rate_limit_exceeded"} if {
	rate_limited_grant
} else := {"allow": false, "reason": "time_window_exceeded"} if {
	time_window_denied_grant
} else := {"allow": false, "reason": "grant_revoked"} if {
	revoked_matching_grant
} else := {"allow": false, "reason": "purpose_not_allowed"} if {
	purpose_mismatch_grant
} else := {"allow": false, "reason": "no_active_grant"} if {
	true
}

active_matching_grant if {
	agent_action_supported
	some grant_id
	grant := data.prism.grants[grant_id]
	base_match(grant)
	grant.status == "active"
	within_time_window(grant)
	within_rate_limit(grant)
}

rate_limited_grant if {
	agent_action_supported
	some grant_id
	grant := data.prism.grants[grant_id]
	base_match(grant)
	grant.status == "active"
	within_time_window(grant)
	not within_rate_limit(grant)
}

time_window_denied_grant if {
	agent_action_supported
	some grant_id
	grant := data.prism.grants[grant_id]
	base_match(grant)
	grant.status == "active"
	not within_time_window(grant)
}

revoked_matching_grant if {
	agent_action_supported
	some grant_id
	grant := data.prism.grants[grant_id]
	base_match(grant)
	grant.status == "revoked"
}

purpose_mismatch_grant if {
	agent_action_supported
	some grant_id
	grant := data.prism.grants[grant_id]
	grant.user_id == input.user_id
	grant.agent_id == input.agent_id
	normalized_data_category(grant) == normalized_input_data_category
	grant.purpose != input.purpose
}

base_match(grant) if {
	grant.user_id == input.user_id
	grant.agent_id == input.agent_id
	normalized_data_category(grant) == normalized_input_data_category
	grant.purpose == input.purpose
}

normalized_data_category(grant) := category if {
	category := object.get(grant, "data_category", "room_messages")
}

normalized_input_data_category := category if {
	category := object.get(input, "data_category", "room_messages")
}

agent_action_supported if {
	input.action in {"read_messages", "collect_messages", "run_skill", "read_memory"}
}

within_time_window(grant) if {
	ts_ns := time.parse_rfc3339_ns(input.ts)
	passes_start(grant, ts_ns)
	passes_end(grant, ts_ns)
}

passes_start(grant, ts_ns) if {
	start := object.get(grant, "time_window_start", null)
	start == null
	ts_ns >= 0
}

passes_start(grant, ts_ns) if {
	start := object.get(grant, "time_window_start", null)
	start != null
	ts_ns >= time.parse_rfc3339_ns(start)
}

passes_end(grant, ts_ns) if {
	end := object.get(grant, "time_window_end", null)
	end == null
	ts_ns >= 0
}

passes_end(grant, ts_ns) if {
	end := object.get(grant, "time_window_end", null)
	end != null
	ts_ns <= time.parse_rfc3339_ns(end)
}

within_rate_limit(grant) if {
	request_count := object.get(input, "request_count_per_minute", 1)
	limit := object.get(grant, "rate_limit_per_minute", 60)
	request_count <= limit
}
