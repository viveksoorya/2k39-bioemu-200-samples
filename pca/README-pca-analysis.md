# working memory for PCA analysis

## pending sections
- [ ] understanding how principal components are calculated
- [ ] getting the principal components requires four steps
- [ ] what does transformed ie weights represent?

## completed sections
- [x] understanding how principal components represent motion
- [x] what is cosine content?

# notes

### understanding how principle components represent motion [done]
1) what are the dimensions here? A dimension is vector of motion; since there are 3N degrees of freedom, where N is the number of atoms, there are 3N dimensions, not 3. Each atom has its own degrees of motion and rotation. This makes the motion of the molecule complex. There might be use cases to finding a handful few axes along which the bulk of the 'net' motion is happening. Motion of an atom can be gleaned from the variation in the coordinates of the atom over all frames.
You can get such variation for all atoms but how does that get you to reduced dimensions. All atoms are necessary and all dimensions of all atoms are necessary.
2) would covariance help and how? You get a matrix of information on how every atoms moves along every dimension is relative to every other atoms movement along every dimension. In other words, how atoms move relative to each other in each of their N 3d spaces.
This information gets us only so far as understanding the relative constrained motion, that is, how much each atom's motion along a particular axis is restricted by other atoms motions along each of their three axes. If the covariance is 0, they are not affected by each other, if the covariance is negative or positive they are affected by each other: if positive, they are likely to both move along each of specific axis each and if negative, motion of an atom along its axis along positive direction would encourage motion of the other atom along its axis along negative direction and vice versa.
From this, we get the information about constraitns;
3) If we can somehow see the cumulative effect of these constraints to see where the maximum positive interference of motion is happening that would get us our principal component.


### understanding how principal components are calculated []
The analysis takes motion files and extracts eigenvectors and eigenvalues that represent the principal components and variances in motion

We get the eigenvectors and eigenvalues from diagonalization of the 3N by 3N covariance matrix

So simply put the principal components are vectors in the eigenvector matrix we get from diagonalizing the covariance matrix.

That's the principal components part; Each principal component being an axis, has motion in it and the motion is described by the variance; The variance is the eigenvalue of the principal component

principal components can be ordered by the variance in each and a plot can be made of the ordered set of principal components, ordered by variance, to show that some principal components carry a lot more motion than others

That said, we can use the principal components to visualize the motion in few important dimensions; It is useful to visualize them in the first few components ordered (descending) by variance, since they capture the bulk of the motion.
    One way to visualize this is by looking at the motion along the pairs of eigenvectors from the set of a significant few, with time as another dimension to see the motion (the variance)
    As mentioned in the documentation, principal component analysis has various algorithms, the visualization should not look different as long as the anlaysis is itself done by just one and the same package.

Bluntly, what does diagonalization do in the PCA?
If A is diagonalized to get B, A and B are related how



### Getting the principal components requires four steps[]:
1
2 covariance matrix of 3N by 3N coordinates
3 diagonalize to get eigenvectors (here interpreted as principal components)
4
All taken care of by the library function pca.PCA()


### What does transformed ie weights represent? []
What is the transformation; 

Transformation has to do with reduced dimensionality representation; 
Still not sure what the transform itself is, in the notebook; 
the transformation takes atomgroups and principal components and gives weights of the atomgroups on the principal components. But what does that signify, how do i interpret that?


Outer product of what and what and why? Outer product of transformed and PCs

Projected then is outer product adjusted to the mean of the principal component

There is an outerproduct per principal component that you are projecting onto.

So for each principal component, there are a bunch of entries. What do the entries in the eigenvector (principal component) represent again? Whatever they represent, they are being multiplied with the scaled eigenvector when the scaling factor is deviation from the mean strucuture. So, this is just scaling an outer product of a vector with itself? It is. But, then what do I make of that?

### What is cosine content? [done]
Cosine content indicates how close the motion in the principal component is close to a cosine. If it is really close, then it is closer to random diffusion and so indicates poor sampling. [0,0.7) indicate acceptable sampling. Cosine content indicates the convergence of the trajectory, and if the convergence is close to a cosine then we have a problem.

What is convergence?



Note: I use the words eigenvectors and principal components interchangebly in this document to ensure I associate them both together. Same with eigenvalues and variance