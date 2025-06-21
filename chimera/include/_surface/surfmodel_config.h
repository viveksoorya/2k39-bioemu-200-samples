#ifndef SURFMODEL_CONFIG_HEADER_INCLUDED
#define SURFMODEL_CONFIG_HEADER_INCLUDED

# ifndef SURFMODEL_DLL
#  if (__GNUC__ > 4) || (__GNUC__ == 4 && (defined(__APPLE__) || __GNUC_MINOR__ >= 3))
#   define SURFMODEL_IMEX __attribute__((__visibility__("default")))
#  else
#   define SURFMODEL_IMEX
#  endif
# elif defined(SURFMODEL_EXPORT)
#  define SURFMODEL_IMEX __declspec(dllexport)
# else
#  define SURFMODEL_IMEX __declspec(dllimport)
# endif

#endif
