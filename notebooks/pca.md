The analysis takes motion files and extracts eigenvectors and eigenvalues that represent the principal components and variances in motion

We get the eigenvectors and eigenvalues from diagonalization of the 3N by 3N covariance matrix

So simply put the principal components are vectors in the eigenvector matrix we get from diagonalizing the covariance matrix.

That's the principal components part; Each principal component being an axis, has motion in it and the motion is described by the variance; The variance is the eigenvalue of the principal component

principal components can be ordered by the variance in each and a plot can be made of the ordered set of principal components, ordered by variance, to show that some principal components carry a lot more motion than others

That said, we can use the principal components to visualize the motion in few important dimensions; It is useful to visualize them in the first few components ordered (descending) by variance, since they capture the bulk of the motion.
    One way to visualize this is by looking at the motion along the pairs of eigenvectors from the set of a significant few, with time as another dimension to see the motion (the variance)
    As mentioned in the documentation, principal component analysis has various algorithms, the visualization should not look different as long as the anlaysis is itself done by just one and the same package.


### Getting the principal components requires four steps:
1
2 covariance matrix of 3N by 3N coordinates
3 diagonalize to get eigenvectors (here interpreted as principal components)
4
All taken care of by the library function pca.PCA()


### What does transformed ie weights represent? 
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