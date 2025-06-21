#ifndef Chimera_BulkStorage_h
# define Chimera_BulkStorage_h

# if defined(_MSC_VER) && (_MSC_VER >= 1020)
#  pragma once
# endif

# ifndef WrapPy

# include <iterator>
# include <algorithm>
# include <vector>

namespace molecule {

// BulkStorage:
//
// 	Like a vector, where the memory is not contiguous, so indexing
// 	into it may be slow, but the address of any element never changes.
// 	So adding elements is fast as things never need to be copied, but
// 	iterating through is slower.
//
// 	Although a random access iterator is provided, you'll get better
// 	performance from a std::vector if you need to sort your data.

template <class T /*, class Allocator = allocator<T>*/ > 
class BulkStorage
{
public:
	typedef T			value_type;
	typedef value_type*		pointer;
	typedef const value_type*	const_pointer;
	typedef value_type&		reference;
	typedef const value_type&	const_reference;
	typedef size_t			size_type;
	typedef ptrdiff_t		difference_type;
private:
	typedef std::vector<pointer> Dir;
	Dir		dir;
	size_type	blockSize;
	size_type	elementsPerBlock;
	size_type	nextElement;
public:
	class iterator: public std::iterator<std::random_access_iterator_tag,
		value_type, difference_type, pointer, reference>
	{
		friend class BulkStorage<T /*, Allocator*/ >;
	protected:
		typename iterator::value_type **baseBlock;
		size_type	element;
		size_type	elementsPerBlock;
		size_type	index;
	public:
		iterator(): baseBlock(0) {}
		bool operator==(const iterator& x) const
		{
			return index == x.index;
		}
		bool operator!=(const iterator& x) const
		{
			return index != x.index;
		}
		typename iterator::reference operator*()
		{
			return (*baseBlock)[element];
		}
		typename iterator::pointer operator->() const
		{
			return &(*baseBlock)[element];
		}
		iterator& operator++()
		{
			++index;
			++element;
			if (element == elementsPerBlock) {
				++baseBlock;
				element = 0;
			}
			return *this;
		}
		iterator operator++(int)
		{
			iterator tmp(*this);
			++*this;
			return tmp;
		}
		iterator& operator--()
		{
			--index;
			if (element != 0)
				--element;
			else {
				--baseBlock;
				element = elementsPerBlock - 1;
			}
			return *this;
		}
		iterator operator--(int)
		{
			iterator tmp(*this);
			--*this;
			return tmp;
		}
		typename iterator::reference operator[](size_type i)
		{
			iterator tmp(*this);
			tmp += i;
			return *tmp;
		}
		iterator& operator+=(typename iterator::difference_type i)
		{
			index += i;
			element += i;
			size_type adjust = element / elementsPerBlock;
			element %= elementsPerBlock;
			if (element < 0) {
				// assume int division and mod are consistent
				element += elementsPerBlock;
				adjust -= 1;
			}
			baseBlock += adjust;
			return *this;
		}
		iterator& operator-=(typename iterator::difference_type i)
		{
			return *this += -i;
		}
		iterator& operator+(typename iterator::difference_type i)
		{
			iterator tmp(*this);
			return tmp += i;
		}
		iterator& operator-(typename iterator::difference_type i)
		{
			iterator tmp(*this);
			return tmp += -i;
		}
		typename iterator::difference_type operator-(const iterator& x) const
		{
			return index - x.index;
		}
		bool operator<(const iterator& x) const
		{
			return index < x.index;
		}
		bool operator>(const iterator& x) const
		{
			return index > x.index;
		}
		bool operator<=(const iterator& x) const
		{
			return index <= x.index;
		}
		bool operator>=(const iterator& x) const
		{
			return index >= x.index;
		}
	};
	class const_iterator: public std::iterator<
		std::bidirectional_iterator_tag, value_type, difference_type,
		const_pointer, const_reference>
	{
		friend class BulkStorage<T /*, Allocator*/ >;
	protected:
		const typename const_iterator::value_type * const *baseBlock;
		size_type	element;
		size_type	elementsPerBlock;
	public:
		const_iterator(): baseBlock(0) {}
		bool operator==(const const_iterator& x) const
		{
			return baseBlock == x.baseBlock && element == x.element;
		}
		bool operator!=(const const_iterator& x) const
		{
			return baseBlock != x.baseBlock || element != x.element;
		}
		typename const_iterator::reference operator*()
		{
			return (*baseBlock)[element];
		}
		typename const_iterator::pointer operator->() const
		{
			return &(*baseBlock)[element];
		}
		const_iterator& operator++()
		{
			++element;
			if (element == elementsPerBlock) {
				baseBlock++;
				element = 0;
			}
			return *this;
		}
		const_iterator operator++(int)
		{
			const_iterator tmp(*this);
			++*this;
			return tmp;
		}
		const_iterator& operator--()
		{
			if (element != 0)
				--element;
			else {
				--baseBlock;
				element = elementsPerBlock - 1;
			}
			return *this;
		}
		const_iterator operator--(int)
		{
			const_iterator tmp(*this);
			--*this;
			return tmp;
		}
	};
	iterator	begin()
			{
				iterator i;
				i.baseBlock = &dir[0];
				i.element = 0;
				i.elementsPerBlock = elementsPerBlock;
				i.index = 0;
				return i;
			}
	iterator	end()
			{
				iterator i;
				i.element = nextElement;
				if (nextElement != 0)
					i.baseBlock = &*dir.rbegin();
				else
					i.baseBlock = &*dir.end();
				i.elementsPerBlock = elementsPerBlock;
				i.index = (dir.size() - 1) * elementsPerBlock
								+ nextElement;
				return i;
			}
	const_iterator	begin() const
			{
				const_iterator i;
				i.baseBlock = &dir[0];
				i.element = 0;
				i.elementsPerBlock = elementsPerBlock;
				return i;
			}
	const_iterator	end() const
			{
				const_iterator i;
				i.element = nextElement;
				if (nextElement != 0)
					i.baseBlock = &*dir.rbegin();
				else
					i.baseBlock = &*dir.end();
				i.elementsPerBlock = elementsPerBlock;
				return i;
			}
	bool		empty() const
			{
				return dir.empty();
			}
	size_type	size() const
			{
				if (dir.empty())
					return 0;
				return (dir.size() - 1) * elementsPerBlock
								+ nextElement;
			}
	size_type	max_size() const
			{
				return size_type(~0) / sizeof (value_type);
			}
	reference	operator[](size_type n)
			{
				return dir[n / elementsPerBlock][n % elementsPerBlock];
			}
	const_reference	operator[](size_type n) const
			{
				return dir[n / elementsPerBlock][n % elementsPerBlock];
			}
	void		clear()
			{
				for (typename Dir::iterator i = dir.begin(); i != dir.end(); ++i)
					delete [] *i;
				dir.clear();
				nextElement = 0;
			}
	reference	extend()
			{
				if (nextElement == 0)
					dir.push_back(new T[elementsPerBlock]);
				pointer v = dir.back();
				reference ref = v[nextElement++];
				if (nextElement == elementsPerBlock)
					nextElement = 0;
				return ref;
			}
	void		push_back(const T& x)
			{
				extend() = x;
			}
	void		swap(BulkStorage<T /*, Allocator*/>& x)
			{
				dir.swap(x.dir);
				std::swap(blockSize, x.blockSize);
				std::swap(elementsPerBlock, x.elementsPerBlock);
				std::swap(nextElement, x.nextElement);
			}

	BulkStorage(): blockSize(8160),
			elementsPerBlock(blockSize / sizeof (value_type)),
			nextElement(0)
			{
			}
	explicit BulkStorage(size_type block_size): blockSize(blockSize),
			elementsPerBlock(blockSize / sizeof (value_type)),
			nextElement(0)
			{
			}
	~BulkStorage()	{
				clear();
			}
	explicit BulkStorage(const BulkStorage &b)
			{
				nextElement = b.nextElement;
				elementsPerBlock = b.elementsPerBlock;
				dir.reserve(b.dir.size());
				for (typename Dir::const_iterator i = b.dir.begin(); i != b.dir.end(); ++i) {
					dir.push_back(new T[elementsPerBlock]);
					std::copy(*i, *i + elementsPerBlock,
								dir.back());
				}
			}
	void		operator=(const BulkStorage &b)
			{
				if (this == &b)
					return;
				clear();
				nextElement = b.nextElement;
				elementsPerBlock = b.elementsPerBlock;
				dir.reserve(b.dir.size());
				for (typename Dir::iterator i = b.dir.begin(); i != b.dir.end(); ++i) {
					dir.push_back(new T[elementsPerBlock]);
					std::copy(*i, *i + elementsPerBlock,
								dir.back());
				}
			}

};

} // namespace molecule

# endif /* WrapPy */

#endif
