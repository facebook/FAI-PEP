#!/usr/bin/env python3
# Copyright 2004-present Facebook. All Rights Reserved.

from typing import Any, Dict, List, Optional


class PerfettoConfig:
    ADAPTIVE_SAMPLING_SHMEM_THRESHOLD_DEFAULT = 32746
    BUFFER_SIZE_KB_DEFAULT = 256 * 1024  # 256 megabytes
    BUFFER_SIZE2_KB_DEFAULT = 2 * 1024  # 2 megabytes
    SHMEM_SIZE_BYTES_DEFAULT = (
        16384 * 4096
    )  # Shared memory buffer value must be a large POWER of 2 of at least 4096
    SAMPLING_INTERVAL_BYTES_DEFAULT = 4096
    DUMP_INTERVAL_MS_DEFAULT = 1000
    BATTERY_POLL_MS_DEFAULT = 1000
    CPU_POLL_MS_DEFAULT = 1000
    MAX_FILE_SIZE_BYTES_DEFAULT = 100000000

    def __init__(
        self,
        types: List[str],
        options: Dict[str, Any],
        *,
        app_name: Optional[str] = "program",
    ):
        self.types = types
        self.options = options
        self.app_name = app_name

    def GeneratePerfettoConfig(self, *, advanced_support: bool = False) -> str:
        """advanced support:   Running at least OS 12 version of Perffeto binary"""
        # Write custom perfetto config
        android_log_config = ""
        cpu_scheduling_details_ftrace_config = ""
        cpu_ftrace_config = ""
        cpu_sys_stats_config = ""
        cpu_syscalls_ftrace_config = ""
        gpu_ftrace_config = ""
        gpu_mem_total_frace_config = ""
        gpu_memory_config = ""
        heapprofd_config = ""
        linux_ftrace_config = ""
        linux_process_stats_config = ""
        power_config = ""
        power_ftrace_config = ""
        power_suspend_resume_config = ""
        track_event_config = ""
        app_name = self.options.get("app_name", self.app_name)
        buffer_size_kb = self.options.get("buffer_size_kb", self.BUFFER_SIZE_KB_DEFAULT)
        buffer_size2_kb = self.options.get(
            "buffer_size2_kb", self.BUFFER_SIZE2_KB_DEFAULT
        )
        max_file_size_bytes = self.options.get(
            "max_file_size_bytes", self.MAX_FILE_SIZE_BYTES_DEFAULT
        )
        if self.options.get("include_android_log", False):
            android_log_config = ANDROID_LOG_CONFIG
        if "memory" in self.types:
            shmem_size_bytes = self.options.get(
                "shmem_size_bytes", self.SHMEM_SIZE_BYTES_DEFAULT
            )
            adaptive_sampling_shmem_threshold = self.options.get(
                "adaptive_sampling_shmem_threshold",
                self.ADAPTIVE_SAMPLING_SHMEM_THRESHOLD_DEFAULT,
            )
            adaptive_sampling_shmem_threshold_config = (
                f"            adaptive_sampling_shmem_threshold: {adaptive_sampling_shmem_threshold}\n"
                if advanced_support
                else ""
            )
            all_heaps_config = (
                "            all_heaps: true\n"
                if self.options.get("all_heaps", False)
                else ""
            )
            sampling_interval_bytes = self.options.get(
                "sampling_interval_bytes", self.SAMPLING_INTERVAL_BYTES_DEFAULT
            )
            dump_interval_ms = self.options.get(
                "dump_interval_ms", self.DUMP_INTERVAL_MS_DEFAULT
            )
            dump_phase_ms = self.options.get("dump_phase_ms", dump_interval_ms)
            heapprofd_config = HEAPPROFD_CONFIG.format(
                all_heaps_config=all_heaps_config,
                shmem_size_bytes=shmem_size_bytes,
                adaptive_sampling_shmem_threshold_config=adaptive_sampling_shmem_threshold_config,
                sampling_interval_bytes=sampling_interval_bytes,
                dump_interval_ms=dump_interval_ms,
                dump_phase_ms=dump_phase_ms,
                app_name=app_name,
            )
        if "battery" in self.types:
            battery_poll_ms = self.options.get(
                "battery_poll_ms", self.BATTERY_POLL_MS_DEFAULT
            )
            power_config = POWER_CONFIG.format(
                battery_poll_ms=battery_poll_ms,
            )
            power_ftrace_config = POWER_FTRACE_CONFIG
            power_suspend_resume_config = POWER_SUSPEND_RESUME_CONFIG

        if "gpu" in self.types:
            gpu_mem_total_frace_config = GPU_MEM_TOTAL_FTRACE_CONFIG
            gpu_memory_config = GPU_MEMORY_CONFIG
            gpu_ftrace_config = GPU_FTRACE_CONFIG.format(
                gpu_mem_total_frace_config=gpu_mem_total_frace_config,
            )

        if "cpu" in self.types:
            cpu_poll_ms = max(
                self.options.get("cpu_poll_ms", self.CPU_POLL_MS_DEFAULT), 100
            )  # minimum is 100ms or error
            log_cpu_scheduling_details = self.options.get(
                "log_cpu_scheduling_details", True
            )
            if self.options.get("log_coarse_cpu_usage", False):
                cpu_sys_stats_config = CPU_SYS_STATS_CONFIG.format(
                    cpu_poll_ms=cpu_poll_ms,
                )
            if self.options.get("log_cpu_sys_calls", False):
                cpu_syscalls_ftrace_config = CPU_SYSCALLS_FTRACE_CONFIG
            if log_cpu_scheduling_details:
                cpu_scheduling_details_ftrace_config = (
                    CPU_SCHEDULING_DETAILS_FTRACE_CONFIG
                )
                linux_process_stats_config = LINUX_PROCESS_STATS_CONFIG.format(
                    cpu_poll_ms=cpu_poll_ms,
                )
            cpu_ftrace_config = CPU_FTRACE_CONFIG
            power_suspend_resume_config = POWER_SUSPEND_RESUME_CONFIG

        if {"battery", "gpu", "cpu"}.intersection(self.types):
            linux_ftrace_config = LINUX_FTRACE_CONFIG.format(
                app_name=app_name,
                cpu_ftrace_config=cpu_ftrace_config,
                cpu_scheduling_details_ftrace_config=cpu_scheduling_details_ftrace_config,
                cpu_syscalls_ftrace_config=cpu_syscalls_ftrace_config,
                gpu_ftrace_config=gpu_ftrace_config,
                power_ftrace_config=power_ftrace_config,
                power_suspend_resume_config=power_suspend_resume_config,
            )

        # Generate config file
        return PERFETTO_CONFIG_TEMPLATE.format(
            max_file_size_bytes=max_file_size_bytes,
            buffer_size_kb=buffer_size_kb,
            buffer_size2_kb=buffer_size2_kb,
            android_log_config=android_log_config,
            cpu_sys_stats_config=cpu_sys_stats_config,
            gpu_memory_config=gpu_memory_config,
            heapprofd_config=heapprofd_config,
            linux_ftrace_config=linux_ftrace_config,
            linux_process_stats_config=linux_process_stats_config,
            power_config=power_config,
            track_event_config=track_event_config,
        )


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
duration_ms: 3600000
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
            continuous_dump_config {{
                dump_phase_ms: {dump_phase_ms}
                dump_interval_ms: {dump_interval_ms}
            }}
            process_cmdline: "{app_name}"
            shmem_size_bytes: {shmem_size_bytes}
{adaptive_sampling_shmem_threshold_config}\
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
