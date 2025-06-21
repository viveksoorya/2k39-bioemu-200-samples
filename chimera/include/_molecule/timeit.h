#ifndef _molecule_timeit_h
#define _molecule_timeit_h

#include <string>
#include <time.h>

namespace molecule {

// Report time between creation and destruction of TimeIt object for profiling
// function and scope run-times.

class TimeIt
{
 public:
  TimeIt(std::string message, bool stack_trace = false);
  virtual ~TimeIt();
 private:
  std::string message;
  bool stack_trace;
  clock_t start;
  static int nested_timers;
};

} // namespace molecule

#endif
