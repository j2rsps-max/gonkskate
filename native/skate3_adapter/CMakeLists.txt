cmake_minimum_required(VERSION 3.25)

# Embed after the upstream SDK has defined rex::runtime. Production links its
# original InputSystem; only the standalone tests compile SDK sources directly.
if(NOT TARGET rex::runtime)
  message(FATAL_ERROR "Define the upstream rex::runtime target before adding this adapter")
endif()
add_library(gonkskate_skate3_input STATIC
  src/skate3_pad.cpp src/skate3_input.cpp src/skate3_driver.cpp)
target_compile_features(gonkskate_skate3_input PUBLIC cxx_std_23)
target_include_directories(gonkskate_skate3_input PUBLIC include)
target_link_libraries(gonkskate_skate3_input PUBLIC rex::runtime)
