# pyre-unsafe
from typing import Tuple

import numpy as np

from utils.custom_logger import getLogger


def get_benchmark_start_end(data, window_size) -> Tuple[int, int]:
    """
    This convolves the power data with a window of size 10 seconds
    with first half filled with -1 and second half with 1.
    This averages out the noise to help us find the start/end of
    the benchmark window.
    """
    assert len(data) >= window_size, "Not enough data to find benchmark start/end"
    assert window_size % 2 == 0, "window size should be even"
    half_window_size = int(window_size / 2)
    conv_output = []
    # first half of the window is filled with -1 and second half with 1
    #                 ,____________+1
    #                 |
    #                 |
    # -1______________|
    # Convolution with the above kernel can be computed as below.
    conv_out = np.sum(data[half_window_size:window_size]) - np.sum(
        data[:half_window_size]
    )
    conv_output.append(conv_out)
    for i in range(0, len(data) - window_size):
        # No need to recompute convolution for the entire window. We can reuse the
        # previous output, and adjust at the first, last and middle.
        # Example: with a window size of 1000
        # The first output, out_0: sum(data[500:1000])-sum(data[0:500])
        # The second output: out_1: sum(data[501:1001])-sum(data[1:501])
        # i.e., out_1 = out_0 + data[0] - 2 * data[500] + data[1000]
        # This reduces convolution complexity from O(M*N) -> O(M)
        conv_out = (
            conv_output[-1]  # previous output (prev)
            + data[i]  # in prev, this was subtracted. Now add it so that it is removed.
            # in prev, this was added. Now subtract it twice for the new window.
            - (2 * data[i + half_window_size])
            + data[i + window_size]  # new sample: add it
        )
        conv_output.append(conv_out)
    conv_output = np.array(conv_output)
    start_ind = np.argmax(conv_output) + half_window_size
    end_ind = np.argmin(conv_output) + half_window_size
    return start_ind, end_ind


def post_process_power_data(power_data, sample_rate, num_iters):
    """
    Post process power data to get the model power and energy
    """
    # creating an averaging window of 10 seconds to filter out noise,
    # to capture the start/end of benchmark window
    window_size = 10 * sample_rate
    power = power_data["total_power"]
    getLogger().info(
        "Post-processing power data to find the start/end of benchmark window"
    )
    benchmark_start_ind, benchmark_end_ind = get_benchmark_start_end(power, window_size)
    benchmark_start_time = benchmark_start_ind / sample_rate
    benchmark_end_time = benchmark_end_ind / sample_rate
    getLogger().info(
        f"Benchmark ran from: {benchmark_start_time:.2f} to {benchmark_end_time:.2f} seconds"
    )
    if benchmark_start_ind > benchmark_end_ind:
        raise Exception("Benchmark failed")
    benchmark_power = np.mean(power[benchmark_start_ind:benchmark_end_ind])
    baseline_power = np.mean(power[benchmark_end_ind:])
    model_power = benchmark_power - baseline_power
    benchmark_time = benchmark_end_time - benchmark_start_time
    inference_time = benchmark_time / num_iters * 1e3  # ms
    data = {
        "power": _composeStructuredData(model_power, "power", "mW"),
        "baseline_power": _composeStructuredData(
            baseline_power, "baseline_power", "mW"
        ),
        "latency": _composeStructuredData(inference_time, "latency", "ms"),
    }
    return data


def _composeStructuredData(data, metric, unit):
    return {
        "values": [data],
        "type": "NET",
        "metric": metric,
        "unit": unit,
        "summary": {
            "p0": data,
            "p10": data,
            "p50": data,
            "p90": data,
            "p100": data,
            "mean": data,
            "stdev": 0,
            "MAD": 0,
        },
    }
