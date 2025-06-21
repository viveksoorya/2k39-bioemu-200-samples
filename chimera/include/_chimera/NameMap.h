#ifndef Chimera_NameMap_h
# define Chimera_NameMap_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

# include <stdexcept>
# include <vector>
# include <utility>
# include "Symbol.h"
# include "_chimera_config.h"

# ifdef CHIMERA_STD_HASH
#  include <hash_map>
# else
#  include <map>
# endif

#ifdef CHIMERA_STD_HASH
namespace std {

template <class klass>
struct hash<klass*> {
	size_t operator()(klass* k) const
	{
#ifdef CHIMERA_64BITPTR
		std::hash<long> h;
		return h(reinterpret_cast<long>(k));
#else
		std::hash<int> h;
		return h(reinterpret_cast<int>(k));
#endif
	}
};

} // namespace std
#endif

namespace chimera {

template <class klass>
class CHIMERA_IMEX Name {
public:
# ifdef CHIMERA_STD_HASH
	typedef std::hash_map<Symbol, Name<klass>*> NameMap;
# else
	typedef std::map<Symbol, Name<klass>*> NameMap;
# endif
	typedef std::pair<typename NameMap::const_iterator, typename NameMap::const_iterator> NameMapRange;
	static klass*	lookup(Symbol name);
	static void	remove(Symbol name) throw ();
	static NameMapRange
			list() throw ();

	Name() {}
	virtual ~Name();
	Symbol	name() const throw ();
	// Use save and remove instead of a setName() api so Python can
	// transfer ownership to C++ on a save and get it back on a remove.
	void		save(Symbol name) throw (std::logic_error);
	void		remove() throw ();
protected:
# ifdef CHIMERA_STD_HASH
	typedef std::hash_map<Name<klass>*, Symbol> BackMap;
# else
	typedef std::map<Name<klass>*, Symbol> BackMap;
# endif
	static NameMap all;
	static BackMap back;
};

} // namespace chimera

# endif /* WrapPy */

#endif
