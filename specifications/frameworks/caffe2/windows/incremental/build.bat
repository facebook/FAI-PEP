setlocal
SET USE_OBSERVERS=ON
SET BUILD_BINARY=ON
call %1\scripts\build_windows.bat || exit /b 1
copy %1\build\bin\Release\caffe2_benchmark.exe %2
endlocal
exit /b 0
