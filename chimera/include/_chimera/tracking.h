#ifndef Chimera_tracking_h
# define Chimera_tracking_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

# include <tk.h>
// undef X.h defines that we use
# undef Always
# undef panic 

namespace chimera {

extern void   trackingXY(Tcl_Interp *interp, Tk_Window win, const char *mode,
								int *x, int *y);

} // namespace chimera

# endif /* WrapPy */

#endif
