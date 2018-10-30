setlocal
rd /Q /S %1\build
SET USE_OBSERVERS=ON
SET USE_CUDA=ON
SET BUILD_BINARY=ON
SET TORCH_CUDA_ARCH_LIST=6.1
call %1\scripts\build_windows.bat || exit /b 1
copy %1\build\bin\Release\caffe2_benchmark.exe %2
endlocal
exit /b 0
