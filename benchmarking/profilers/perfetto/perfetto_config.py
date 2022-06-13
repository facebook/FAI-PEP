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
{cpu_sys_stats_config}
{power_config}\
{heapprofd_config}\
{linux_process_stats_config}\
{gpu_memory_config}\
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
data_sources: {{
    config {{
        name: "linux.process_stats"
        target_buffer: 0
        process_stats_config {{
            scan_all_processes_on_start: false
            proc_stats_poll_ms: {cpu_poll_ms}
        }}
    }}
}}
"""

CPU_SYS_STATS_CONFIG = """\
data_sources: {{
    config {{
        name: "linux.sys_stats"
        sys_stats_config {{
            stat_period_ms: {cpu_poll_ms}
            stat_counters: STAT_CPU_TIMES
            stat_counters: STAT_FORK_COUNT
        }}
    }}
}}
"""

GPU_MEMORY_CONFIG = """\
data_sources: {
    config {
        name: "android.gpu.memory"
    }
}
"""

GPU_MEM_TOTAL_FTRACE_CONFIG = """\
            ftrace_events: "gpu_mem/gpu_mem_total"
"""

GPU_FTRACE_CONFIG = """\
            ftrace_events: "gpu_frequency"
{gpu_mem_total_frace_config}\
"""

CPU_FTRACE_CONFIG = """\
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
"""

CPU_SYSCALLS_FTRACE_CONFIG = """\
            ftrace_events: "raw_syscalls/sys_enter"
            ftrace_events: "raw_syscalls/sys_exit"
"""

CPU_SCHEDULING_DETAILS_FTRACE_CONFIG = """\
            ftrace_events: "sched/sched_switch"
            ftrace_events: "sched/sched_wakeup"
            ftrace_events: "sched/sched_wakeup_new"
            ftrace_events: "sched/sched_waking"
            ftrace_events: "sched/sched_process_exit"
            ftrace_events: "sched/sched_process_free"
            ftrace_events: "task/task_newtask"
            ftrace_events: "task/task_rename"
            buffer_size_kb: 2048
            drain_period_ms: 250
"""

POWER_FTRACE_CONFIG = """\
            ftrace_events: "regulator/regulator_set_voltage"
            ftrace_events: "regulator/regulator_set_voltage_complete"
            ftrace_events: "power/clock_enable"
            ftrace_events: "power/clock_disable"
            ftrace_events: "power/clock_set_rate"
"""

POWER_SUSPEND_RESUME_CONFIG = """\
            ftrace_events: "power/suspend_resume"
"""

LINUX_FTRACE_CONFIG = """\
data_sources: {{
    config {{
        name: "linux.ftrace"
        ftrace_config {{
            atrace_apps: "{app_name}"
{gpu_ftrace_config}\
{power_ftrace_config}\
{power_suspend_resume_config}\
{cpu_ftrace_config}\
{cpu_syscalls_ftrace_config}\
{cpu_scheduling_details_ftrace_config}\
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
