cmake_minimum_required(VERSION 3.18)
project(gslib VERSION 1.0.9 LANGUAGES C)

include(GNUInstallDirs)
include(CTest)

set(LIBNAME gs CACHE STRING "Library name")
set(CPREFIX gslib_ CACHE STRING "C symbol prefix")
set(FPREFIX fgslib_ CACHE STRING "Fortran symbol prefix")
option(MPI "Enable MPI support" ON)
option(ADDUS "Append underscores to Fortran symbols" ON)
option(USREXIT "Use an application-provided exit handler" OFF)
option(NBC "Enable nonblocking MPI collectives" OFF)
option(BLAS "Use CBLAS instead of the built-in implementation" OFF)
option(MKL "Use Intel oneMKL for CBLAS" OFF)
option(STATIC "Build a static library" ON)
option(SHARED "Build a shared library" OFF)
option(GSLIB_CODE_PROTETION "Remove source/build names and paths from the static library" OFF)

if(GSLIB_CODE_PROTETION)
  if(NOT MSVC OR SHARED OR NOT CMAKE_BUILD_TYPE MATCHES "^(Release|MinSizeRel)$")
    message(FATAL_ERROR "GSLIB_CODE_PROTETION requires MSVC, a static library, and Release or MinSizeRel")
  endif()
  find_package(Python3 3.8 REQUIRED COMPONENTS Interpreter)
  find_program(GSLIB_LLVM_AR llvm-ar HINTS "$ENV{IFORT_COMPILER25}/bin/compiler")
  if(NOT GSLIB_LLVM_AR)
    message(FATAL_ERROR "GSLIB_CODE_PROTETION requires llvm-ar; set GSLIB_LLVM_AR")
  endif()
endif()

if(NOT STATIC AND NOT SHARED)
  message(FATAL_ERROR "Enable STATIC or SHARED to build a library")
endif()
if(NBC AND NOT MPI)
  message(FATAL_ERROR "NBC requires MPI")
endif()
if(MKL)
  set(BLAS ON)
endif()

set(gslib_definitions GSLIB_PREFIX=${CPREFIX} GSLIB_FPREFIX=${FPREFIX}
                      GSLIB_USE_GLOBAL_LONG_LONG)
if(GSLIB_CODE_PROTETION)
  list(APPEND gslib_definitions GSLIB_CODE_PROTETION)
endif()
set(GSLIB_USE_MPI ${MPI})
set(GSLIB_UNDERSCORE ${ADDUS})
set(GSLIB_USE_USR_EXIT ${USREXIT})
set(GSLIB_USE_NBC ${NBC})
set(GSLIB_USE_CBLAS ${BLAS})
set(GSLIB_USE_MKL ${MKL})
if(NOT BLAS)
  set(GSLIB_USE_NAIVE_BLAS ON)
endif()
foreach(feature USE_MPI UNDERSCORE USE_USR_EXIT USE_NBC USE_CBLAS USE_MKL USE_NAIVE_BLAS)
  if(GSLIB_${feature})
    list(APPEND gslib_definitions GSLIB_${feature})
  endif()
endforeach()

set(gslib_dependencies)
if(MPI)
  find_package(MPI REQUIRED COMPONENTS C)
  list(APPEND gslib_dependencies MPI::MPI_C)
endif()
if(MKL)
  find_package(MKL CONFIG REQUIRED HINTS "$ENV{MKLROOT}/lib/cmake/mkl")
  list(APPEND gslib_dependencies MKL::MKL)
elseif(BLAS)
  find_package(BLAS REQUIRED)
  find_path(CBLAS_INCLUDE_DIR cblas.h REQUIRED)
  list(APPEND gslib_dependencies ${BLAS_LIBRARIES})
endif()
if(NOT WIN32)
  list(APPEND gslib_dependencies m)
endif()

# Match the GNU Make install layout for both build-tree and installed consumers.
set(gslib_include_dir "${CMAKE_CURRENT_BINARY_DIR}/include")
file(GLOB gslib_headers CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/*.h")
foreach(header IN LISTS gslib_headers)
  get_filename_component(name "${header}" NAME)
  configure_file("${header}" "${gslib_include_dir}/gslib/${name}" COPYONLY)
endforeach()
configure_file(cmake/config.h.in "${gslib_include_dir}/gslib/config.h" @ONLY)
configure_file(cmake/gslib.h.in "${gslib_include_dir}/gslib.h" COPYONLY)

set(gslib_sources
  src/gs.c src/sort.c src/sarray_transfer.c src/sarray_sort.c
  src/gs_local.c src/fail.c src/crystal.c src/comm.c src/tensor.c
  src/fcrystal.c src/findpts.c src/findpts_local.c src/obbox.c
  src/poly.c src/lob_bnd.c src/findpts_el_3.c src/findpts_el_2.c)

set(gslib_targets)
if(STATIC)
  add_library(gs STATIC ${gslib_sources})
  list(APPEND gslib_targets gs)
endif()
if(SHARED)
  if(STATIC)
    add_library(gs_shared SHARED ${gslib_sources})
    list(APPEND gslib_targets gs_shared)
  else()
    add_library(gs SHARED ${gslib_sources})
    list(APPEND gslib_targets gs)
  endif()
endif()
add_library(gslib::gs ALIAS gs)
foreach(target IN LISTS gslib_targets)
  target_compile_features(${target} PUBLIC c_std_11)
  target_compile_definitions(${target} PUBLIC ${gslib_definitions})
  target_include_directories(${target} PUBLIC
    $<BUILD_INTERFACE:${gslib_include_dir}>
    $<BUILD_INTERFACE:${gslib_include_dir}/gslib>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/gslib>)
  if(BLAS AND NOT MKL)
    target_include_directories(${target} PUBLIC "${CBLAS_INCLUDE_DIR}")
  endif()
  target_link_libraries(${target} PUBLIC ${gslib_dependencies})
  set_target_properties(${target} PROPERTIES OUTPUT_NAME "${LIBNAME}"
    WINDOWS_EXPORT_ALL_SYMBOLS ON)
  if(WIN32 AND STATIC AND SHARED AND target STREQUAL "gs_shared")
    set_target_properties(${target} PROPERTIES ARCHIVE_OUTPUT_NAME "${LIBNAME}_dll")
  endif()
  if(GSLIB_CODE_PROTETION)
    set_property(TARGET ${target} APPEND PROPERTY LINK_DEPENDS
      "${CMAKE_CURRENT_SOURCE_DIR}/tools/protect_library.py")
    add_custom_command(TARGET ${target} POST_BUILD
      COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/protect_library.py"
        --library "$<TARGET_FILE:${target}>" --source-dir "${CMAKE_CURRENT_SOURCE_DIR}/src"
        --ar "${GSLIB_LLVM_AR}"
      VERBATIM COMMENT "Removing and verifying source/build information")
  endif()
endforeach()

install(TARGETS ${gslib_targets}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES ${gslib_headers} "${gslib_include_dir}/gslib/config.h"
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/gslib)
install(FILES "${gslib_include_dir}/gslib.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

if(BUILD_TESTING)
  set(gslib_tests sort_test sort_test2 sarray_sort_test comm_test crystal_test
    sarray_transfer_test gs_test gs_test_gop_blocking gs_test_gop_nonblocking
    gs_unique_test findpts_el_2_test findpts_el_2_test2 findpts_el_3_test
    findpts_el_3_test2 findpts_local_test findpts_test findpts_test_ms
    poly_test lob_bnd_test obbox_test)
  set(gslib_mpi_tests comm_test crystal_test sarray_transfer_test gs_test
    gs_test_gop_blocking gs_test_gop_nonblocking gs_unique_test
    findpts_test findpts_test_ms)
  foreach(test IN LISTS gslib_tests)
    add_executable(${test} tests/${test}.c)
    target_link_libraries(${test} PRIVATE gslib::gs)
    if(MPI AND MPIEXEC_EXECUTABLE AND test IN_LIST gslib_mpi_tests)
      foreach(ranks 1 2)
        add_test(NAME ${test}_mpi_${ranks} COMMAND "${MPIEXEC_EXECUTABLE}"
          ${MPIEXEC_NUMPROC_FLAG} ${ranks} ${MPIEXEC_PREFLAGS}
          $<TARGET_FILE:${test}> ${MPIEXEC_POSTFLAGS})
        set_tests_properties(${test}_mpi_${ranks} PROPERTIES TIMEOUT 180 PROCESSORS ${ranks})
      endforeach()
    else()
      add_test(NAME ${test} COMMAND ${test})
      set_tests_properties(${test} PROPERTIES TIMEOUT 180)
    endif()
  endforeach()
  if(WIN32)
    # This upstream test expects exactly 39 failures from a nonportable rand() sequence.
    set_tests_properties(findpts_el_2_test2 PROPERTIES DISABLED TRUE)
    message(STATUS "findpts_el_2_test2 is built but disabled: platform-specific rand() baseline")
  endif()
  if(GSLIB_CODE_PROTETION)
    add_executable(protection_diagnostic_test tests/protection_diagnostic_test.c)
    target_link_libraries(protection_diagnostic_test PRIVATE gslib::gs)
    add_test(NAME protection_diagnostic_test COMMAND protection_diagnostic_test)
    set_tests_properties(protection_diagnostic_test PROPERTIES
      PASS_REGULAR_EXPRESSION "protection diagnostic"
      FAIL_REGULAR_EXPRESSION "private|source_file")
    add_test(NAME protection_metadata_test COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/protection_metadata_test.py")
    add_test(NAME protection_binary_test COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tools/protect_library.py"
      --library "$<TARGET_FILE:gs>" --source-dir "${CMAKE_CURRENT_SOURCE_DIR}/src" --verify-only)
  endif()
endif()
