# GSLIB 

[![Build Status](https://travis-ci.org/gslib/gslib.svg?branch=master)](https://travis-ci.org/gslib/gslib)

* Scalable Many-to-Many (neighborhood) gather-scatter collectives
* Robust GLL interpolation on hexahedral spectral element meshes

# Build Instructions

The build system relies on GNU Make with the `make` command. To compile gslib just run:

```
make CC=mpicc
```

Different make options are available (see Makefile).

## Windows with MSVC

Install Visual Studio 2022 C++ build tools (including CMake), Microsoft MPI
(runtime and SDK), and add `jom.exe` to `PATH`. From the repository root run:

```bat
tools\build-msvc.cmd jom
tools\build-msvc.cmd nmake
```

Each command loads the MSVC x64 environment, builds a Release static library
with `cl`, runs the existing C tests (including one- and two-rank MPI
tests), and installs `gs.lib` and headers into `build/msvc-jom/install` or
`build/msvc-nmake/install`. A failed build or test stops the script.

For manual configuration in an x64 Visual Studio developer command prompt:

```bat
cmake -S . -B build/msvc-jom -G "NMake Makefiles JOM" -DCMAKE_C_COMPILER=cl -DCMAKE_BUILD_TYPE=Release -DNBC=ON
cmake --build build/msvc-jom --parallel
ctest --test-dir build/msvc-jom --output-on-failure
cmake --install build/msvc-jom --prefix build/msvc-jom/install
```

CMake supports the existing `MPI`, `ADDUS`, `USREXIT`, `NBC`, `BLAS`, `MKL`,
`STATIC`, `SHARED`, `LIBNAME`, `CPREFIX`, and `FPREFIX` settings. Generated
configuration headers stay in the build directory. Use `-DMPI=OFF` for a
serial build, `-DBUILD_TESTING=OFF` to omit tests, or `-DBLAS=ON -DMKL=ON`
to use oneMKL. Enabling `USREXIT` requires the application to supply the
Fortran exit handler.

On Windows, `findpts_el_2_test2` is compiled but disabled in CTest because
its upstream assertion expects exactly 39 failed points from a specific
platform's `rand()` sequence. The other tests run normally.

Pass `-DGSLIB_CODE_PROTETION=ON` to CMake, or run
`tools\build-msvc.cmd jom ON` (also accepts `nmake ON`), to remove source
filenames and source/build paths from the static library. The spelling
`PROTETION` is intentional. The option defaults to `OFF` and requires MSVC,
a static x64 Release/MinSizeRel build, and Python 3.8 or newer. It uses
MSVC's own `cl.exe` and `lib.exe`; no LLVM, Intel compiler, or obfuscating
compiler is required. Python only cleans and checks file/path metadata.
Diagnostics omit source locations, COFF file metadata is anonymized, and
archive members use numeric identifiers. Each protected library is scanned
before installation; remaining source filenames or build paths fail the
build. Public API symbols and required system library names remain available
for linking. Build logs, installed source headers, and downstream application
debug information are outside this option's scope.

# Applications

**\[1]&#160;[Nek5000](https://nek5000.mcs.anl.gov/)**: Nek5000 open-source, spectral element code.

**\[2]&#160;[CEED](http://ceed.exascaleproject.org/)**: Co-design center for Efficient Exascale Discretizations.

**\[3]&#160;[Nektar++](http://www.nektar.info)**: Nektar++ open-source spectral/hp element code.

**\[4]&#160;[Libparanumal](https://github.com/paranumal/libparanumal)**: Accelerated finite element flow solvers .
