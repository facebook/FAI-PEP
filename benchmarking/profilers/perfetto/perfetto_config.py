#!/usr/bin/env python3
# Copyright 2004-present Facebook. All Rights Reserved.


# duration_ms: {duration_ms}
# max_file_size_bytes: 10000000000

PERFETTO_CONFIG_TEMPLATE = """\
buffers: {{
    size_kb: {buffer_size_kb}
    fill_policy: RING_BUFFER
}}
buffers: {{
    size_kb: {buffer_size2_kb}
    fill_policy: RING_BUFFER
}}
{power_config}\
{heapprofd_config}\
{linux_process_stats_config}\
{linux_ftrace_config}\
{android_log_config}\
{track_event_config}\
write_into_file: true
file_write_period_ms: 2500
max_file_size_bytes: {max_file_size_bytes}
flush_period_ms: 30000
incremental_state_config {{
    clear_period_ms: 5000
}}
"""

POWER_CONFIG = """\
data_sources: {{
    config {{
        name: "android.power"
        android_power_config {{
            battery_poll_ms: {battery_poll_ms}
            battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
            battery_counters: BATTERY_COUNTER_CHARGE
            battery_counters: BATTERY_COUNTER_CURRENT
            collect_power_rails: true
        }}
    }}
}}
"""

HEAPPROFD_CONFIG = """\
data_sources: {{
    config {{
        name: "android.heapprofd"
        target_buffer: 0
        heapprofd_config {{
            sampling_interval_bytes: {sampling_interval_bytes}
            process_cmdline: "{app_name}"
            shmem_size_bytes: {shmem_size_bytes}
            block_client: true
{all_heaps_config}\
        }}
    }}
}}
"""

ANDROID_LOG_CONFIG = """\
data_sources: {
    config {
        name: "android.log"
        target_buffer: 0
        android_log_config {
            min_prio: PRIO_INFO
            log_ids: LID_DEFAULT
            log_ids: LID_RADIO
            log_ids: LID_EVENTS
            log_ids: LID_SYSTEM
            log_ids: LID_CRASH
            log_ids: LID_KERNEL
        }
    }
}
"""

LINUX_PROCESS_STATS_CONFIG = """\
data_sources: {
    config {
        name: "linux.process_stats"
        target_buffer: 0
        process_stats_config {
            scan_all_processes_on_start: true
            proc_stats_poll_ms: 1000
        }
    }
}
"""

LINUX_FTRACE_CONFIG = """\
data_sources: {{
    config {{
        name: "linux.ftrace"
        ftrace_config {{
            atrace_apps: "{app_name}"
            ftrace_events: "regulator/regulator_set_voltage"
            ftrace_events: "regulator/regulator_set_voltage_complete"
            ftrace_events: "power/clock_enable"
            ftrace_events: "power/clock_disable"
            ftrace_events: "power/clock_set_rate"
            ftrace_events: "power/suspend_resume"
        }}
    }}
}}
"""

TRACK_EVENT_CONFIG = """\
data_sources: {
    config {
        name: "track_event"
        target_buffer: 1
    }
}
"""
