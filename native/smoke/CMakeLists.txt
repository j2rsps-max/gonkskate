cmake_minimum_required(VERSION 3.20)
project(gonkskate_abi_smoke LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(gonkskate_abi_smoke main.cpp)
target_include_directories(gonkskate_abi_smoke PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../thug_adapter/include"
)

include(CTest)
add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../thug_adapter" thug-parameters)
