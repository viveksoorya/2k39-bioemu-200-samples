#ifndef Chimera_extra_h
# define Chimera_extra_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# include "_chimera_config.h"
# include <sstream>

extern "C" {
typedef struct _object PyObject;
}

namespace chimera {

extern void initializeColors(bool nogui);
CHIMERA_IMEX extern PyObject *memoryMap(void *start, int len, int type);
CHIMERA_IMEX extern std::string opengl_platform();
CHIMERA_IMEX extern long opengl_getInt(const std::string& parameter);
CHIMERA_IMEX extern double opengl_getFloat(const std::string& parameter);
CHIMERA_IMEX extern void tweak_graphics(const std::string& parameter, bool value);
CHIMERA_IMEX extern std::string xml_quote(std::string s);

#ifndef WrapPy
CHIMERA_IMEX extern void replyobj(const std::string& msg,
					const std::string &func);
// Usage pattern:
//	std::ostringstream s;
//	s << "my message here";
//	replyobj(s.str(), "message");
// where "message" is the replyobj function that will be called
// with the string as its single argument.  The replyobj function
// is not executed immediately, but rather is executed in the main
// python thread by the interpreter "at the earliest convenience".
// This means the calling C++ function will run to completion
// before the replyobj function is called.
//
// This function is mainly intended to report errors from functions
// where throwing an exception is not practical (e.g., when rendering
// graphics).  It is also useful for logging informational messages
// such as computed values without having to modify the Python layer.
#endif

} // namespace chimera

#endif
