#ifndef ChimeraPath_chimerapath_config_h
# define ChimeraPath_chimerapath_config_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef CHIMERAPATH_DLL
#  if (__GNUC__ > 4) || (__GNUC__ == 4 && (defined(__APPLE__) || __GNUC_MINOR__ >= 3))
#   define CHIMERAPATH_IMEX __attribute__((__visibility__("default")))
#  else
#   define CHIMERAPATH_IMEX
#  endif
# elif defined(CHIMERAPATH_EXPORT)
#  define CHIMERAPATH_IMEX __declspec(dllexport)
# else
#  define CHIMERAPATH_IMEX __declspec(dllimport)
# endif

#endif
