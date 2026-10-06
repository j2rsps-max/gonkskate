# C ABI import works with both Skate's MSVC/Clang and the standalone GNU ABI.
# Call only for an explicitly staged, validated production runtime directory.
function(gonkskate_embed_thug host runtime_directory)
    add_library(gonkskate_thug_runtime SHARED IMPORTED)
    set_target_properties(gonkskate_thug_runtime PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${runtime_directory}/include")
    if(WIN32)
        if(NOT EXISTS "${runtime_directory}/gonkskate-thug-runtime.lib")
            message(FATAL_ERROR "Stage the Windows THUG runtime for a Windows frontend build")
        endif()
        set_target_properties(gonkskate_thug_runtime PROPERTIES
            IMPORTED_LOCATION "${runtime_directory}/gonkskate-thug-runtime.dll"
            IMPORTED_IMPLIB "${runtime_directory}/gonkskate-thug-runtime.lib")
    else()
        if(NOT EXISTS "${runtime_directory}/libgonkskate-thug-runtime.so")
            message(FATAL_ERROR "Stage the Linux THUG runtime for a Linux frontend build")
        endif()
        set_target_properties(gonkskate_thug_runtime PROPERTIES
            IMPORTED_LOCATION "${runtime_directory}/libgonkskate-thug-runtime.so")
        set_property(TARGET ${host} APPEND PROPERTY BUILD_RPATH "$ORIGIN")
    endif()
    target_link_libraries(${host} PRIVATE gonkskate_thug_runtime)
    add_custom_command(TARGET ${host} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:gonkskate_thug_runtime> $<TARGET_FILE_DIR:${host}>)
endfunction()
