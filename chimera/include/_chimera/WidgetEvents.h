#ifndef Chimera_ButtonEvents_h
# define Chimera_ButtonEvents_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

namespace chimera {

//
// Restrict Tk event loop to process only events on the specified window.
// This is to detect clicks on "halt" buttons during computations without
// allowing other events to be processed.  Window argument is winfo id of
// Tk window.  Window argument 0 returns to processing all events.
// Calls to this routine do not process any events.
//
void restrictEventProcessing(unsigned long window);

// alternatively, key is a particular key you want to process (given as
// a string so that the Python layer can distinguish the two calls)
void restrictEventProcessing(const char *key);

} // namespace chimera


#endif
