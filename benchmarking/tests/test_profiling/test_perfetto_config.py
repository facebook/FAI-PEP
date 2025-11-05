# pyre-strict
import unittest

from profilers.perfetto.perfetto_config import PerfettoConfig


class PerfettoConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None
        pass

    def test_generate_perfetto_config_memory(self) -> None:
        types = ["memory"]
        options = {}
        expected = self.MEMORY_CONFIG

        config_str = PerfettoConfig(types, options).GeneratePerfettoConfig()
        self.assertEqual(config_str, expected)

    def test_generate_perfetto_config_memory_with_log(self) -> None:
        types = ["memory"]
        options = {"include_android_log": True}
        expected = self.MEMORY_CONFIG_WITH_LOG

        config_str = PerfettoConfig(types, options).GeneratePerfettoConfig()
        self.assertEqual(config_str, expected)

    def test_generate_perfetto_config_battery(self) -> None:
        types = ["battery"]
        options = {}
        expected = self.BATTERY_CONFIG

        config_str = PerfettoConfig(types, options).GeneratePerfettoConfig()
        self.assertEqual(config_str, expected)

    def test_generate_perfetto_config_gpu(self) -> None:
        types = ["gpu"]
        options = {}
        expected = self.GPU_CONFIG

        config_str = PerfettoConfig(types, options).GeneratePerfettoConfig()
        self.assertEqual(config_str, expected)

    def test_generate_perfetto_config_cpu(self) -> None:
        types = ["cpu"]
        options = {}
        expected = self.CPU_CONFIG

        config_str = PerfettoConfig(types, options).GeneratePerfettoConfig()
        self.assertEqual(config_str, expected)

    def test_generate_perfetto_config_cpu_gpu_memory(self) -> None:
        types = ["cpu", "gpu", "memory"]
        options = {}
        expected = self.CPU_GPU_MEMORY_CONFIG

        config_str = PerfettoConfig(types, options).GeneratePerfettoConfig()
        self.assertEqual(config_str, expected)

    """ How to add additional test cases:
        1. Run a successful benchmark with perfetto enabled and given a certain set of types and options
        2. Go to the results page, open the "Perfetto Report" link, and copy the contents
        3. Add the lines <RUN_DESCRIPTION>_CONFIG = <3 quotes><backslash>\n<paste>\n<3 quotes> as below
        4. Add a new test case setting the corresponding values for types, options, and expected.
    """

    MEMORY_CONFIG = """\
buffers: {
    size_kb: 262144
    fill_policy: RING_BUFFER
}
buffers: {
    size_kb: 2048
    fill_policy: RING_BUFFER
}

data_sources: {
    config {
        name: "android.heapprofd"
        target_buffer: 0
        heapprofd_config {
            sampling_interval_bytes: 4096
            continuous_dump_config {
                dump_phase_ms: 1000
                dump_interval_ms: 1000
            }
            process_cmdline: "program"
            shmem_size_bytes: 67108864
            block_client: true
        }
    }
}
duration_ms: 3600000
write_into_file: true
file_write_period_ms: 2500
max_file_size_bytes: 100000000
flush_period_ms: 30000
incremental_state_config {
    clear_period_ms: 5000
}
"""

    MEMORY_CONFIG_WITH_LOG = """\
buffers: {
    size_kb: 262144
    fill_policy: RING_BUFFER
}
buffers: {
    size_kb: 2048
    fill_policy: RING_BUFFER
}

data_sources: {
    config {
        name: "android.heapprofd"
        target_buffer: 0
        heapprofd_config {
            sampling_interval_bytes: 4096
            continuous_dump_config {
                dump_phase_ms: 1000
                dump_interval_ms: 1000
            }
            process_cmdline: "program"
            shmem_size_bytes: 67108864
            block_client: true
        }
    }
}
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
duration_ms: 3600000
write_into_file: true
file_write_period_ms: 2500
max_file_size_bytes: 100000000
flush_period_ms: 30000
incremental_state_config {
    clear_period_ms: 5000
}
"""

    BATTERY_CONFIG = """\
buffers: {
    size_kb: 262144
    fill_policy: RING_BUFFER
}
buffers: {
    size_kb: 2048
    fill_policy: RING_BUFFER
}

data_sources: {
    config {
        name: "android.power"
        android_power_config {
            battery_poll_ms: 1000
            battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
            battery_counters: BATTERY_COUNTER_CHARGE
            battery_counters: BATTERY_COUNTER_CURRENT
            collect_power_rails: true
        }
    }
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            atrace_apps: "program"
            ftrace_events: "regulator/regulator_set_voltage"
            ftrace_events: "regulator/regulator_set_voltage_complete"
            ftrace_events: "power/clock_enable"
            ftrace_events: "power/clock_disable"
            ftrace_events: "power/clock_set_rate"
            ftrace_events: "power/suspend_resume"
        }
    }
}
duration_ms: 3600000
write_into_file: true
file_write_period_ms: 2500
max_file_size_bytes: 100000000
flush_period_ms: 30000
incremental_state_config {
    clear_period_ms: 5000
}
"""

    GPU_CONFIG = """\
buffers: {
    size_kb: 262144
    fill_policy: RING_BUFFER
}
buffers: {
    size_kb: 2048
    fill_policy: RING_BUFFER
}

data_sources: {
    config {
        name: "android.gpu.memory"
    }
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            atrace_apps: "program"
            ftrace_events: "gpu_frequency"
            ftrace_events: "gpu_mem/gpu_mem_total"
        }
    }
}
duration_ms: 3600000
write_into_file: true
file_write_period_ms: 2500
max_file_size_bytes: 100000000
flush_period_ms: 30000
incremental_state_config {
    clear_period_ms: 5000
}
"""

    CPU_CONFIG = """\
buffers: {
    size_kb: 262144
    fill_policy: RING_BUFFER
}
buffers: {
    size_kb: 2048
    fill_policy: RING_BUFFER
}

data_sources: {
    config {
        name: "linux.process_stats"
        target_buffer: 0
        process_stats_config {
            scan_all_processes_on_start: false
            proc_stats_poll_ms: 1000
        }
    }
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            atrace_apps: "program"
            ftrace_events: "power/suspend_resume"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
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
        }
    }
}
duration_ms: 3600000
write_into_file: true
file_write_period_ms: 2500
max_file_size_bytes: 100000000
flush_period_ms: 30000
incremental_state_config {
    clear_period_ms: 5000
}
"""

    CPU_GPU_MEMORY_CONFIG = """\
buffers: {
    size_kb: 262144
    fill_policy: RING_BUFFER
}
buffers: {
    size_kb: 2048
    fill_policy: RING_BUFFER
}

data_sources: {
    config {
        name: "android.heapprofd"
        target_buffer: 0
        heapprofd_config {
            sampling_interval_bytes: 4096
            continuous_dump_config {
                dump_phase_ms: 1000
                dump_interval_ms: 1000
            }
            process_cmdline: "program"
            shmem_size_bytes: 67108864
            block_client: true
        }
    }
}
data_sources: {
    config {
        name: "linux.process_stats"
        target_buffer: 0
        process_stats_config {
            scan_all_processes_on_start: false
            proc_stats_poll_ms: 1000
        }
    }
}
data_sources: {
    config {
        name: "android.gpu.memory"
    }
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            atrace_apps: "program"
            ftrace_events: "gpu_frequency"
            ftrace_events: "gpu_mem/gpu_mem_total"
            ftrace_events: "power/suspend_resume"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
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
        }
    }
}
duration_ms: 3600000
write_into_file: true
file_write_period_ms: 2500
max_file_size_bytes: 100000000
flush_period_ms: 30000
incremental_state_config {
    clear_period_ms: 5000
}
"""
