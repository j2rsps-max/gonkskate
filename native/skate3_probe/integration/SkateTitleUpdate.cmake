# Copy local inputs into the private build tree. The caller supplies inspected
# TU3 hashes; codegen/runtime loaders consume XEX + adjacent XEXP files there.
function(gonkskate_stage_installed_tu game_root patch_root output_root default_hash webkit_hash)
    foreach(relative default.xex data/webkit/EAWebkit.xex)
        if(NOT EXISTS "${game_root}/${relative}")
            message(FATAL_ERROR "Missing local codegen input: ${game_root}/${relative}")
        endif()
    endforeach()
    foreach(relative default.xexp data/webkit/EAWebkit.xexp)
        if(NOT EXISTS "${patch_root}/${relative}")
            message(FATAL_ERROR "Missing installed TU3 patch: ${patch_root}/${relative}")
        endif()
        file(SHA256 "${patch_root}/${relative}" actual)
        if(relative STREQUAL "default.xexp")
            set(expected "${default_hash}")
        else()
            set(expected "${webkit_hash}")
        endif()
        if(NOT actual STREQUAL expected)
            message(FATAL_ERROR "Installed TU3 patch hash differs: ${relative}")
        endif()
    endforeach()
    add_custom_command(OUTPUT
        "${output_root}/default.xex" "${output_root}/default.xexp"
        "${output_root}/data/webkit/EAWebkit.xex" "${output_root}/data/webkit/EAWebkit.xexp"
        COMMAND ${CMAKE_COMMAND} -E make_directory "${output_root}/data/webkit"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${game_root}/default.xex" "${output_root}/default.xex"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${game_root}/data/webkit/EAWebkit.xex" "${output_root}/data/webkit/EAWebkit.xex"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${patch_root}/default.xexp" "${output_root}/default.xexp"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${patch_root}/data/webkit/EAWebkit.xexp" "${output_root}/data/webkit/EAWebkit.xexp"
        DEPENDS "${game_root}/default.xex" "${game_root}/data/webkit/EAWebkit.xex"
            "${patch_root}/default.xexp" "${patch_root}/data/webkit/EAWebkit.xexp"
        COMMENT "Staging hash-verified installed TU3 patches for private codegen"
        VERBATIM)
endfunction()
