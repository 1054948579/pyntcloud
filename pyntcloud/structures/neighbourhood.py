#  HAKUNA MATATA

"""
Neighbourhood Class
"""

import numpy as np
from scipy.stats import zscore

class Neighbourhood(object):
    
    def __init__(self, kdtree, k, eigen=True, **kwargs):
        """
        Parameters
        ----------         
        """
        print("Querying KDTREE...")
        d, i = kdtree.query(kdtree.data, k=k, n_jobs=-1, **kwargs)
        # discard self neighbour with [:,1:]
        self.points = kdtree.data
        self.distances = d[:,1:]
        self.indices = i[:,1:]
        self.k = k - 1
        self.id = "{}-{}".format(kdtree.id, self.k)
        
        if eigen:
            print("Computing eigen decomposition...")
            self.eigen_decomposition()
    
    def eigen_decomposition(self):
        
        neighbours = self.points[self.indices]

        diffs = neighbours - neighbours.mean(1,keepdims=True)
    
        cov_3D = np.einsum('ijk,ijl->ikl',diffs,diffs) / neighbours.shape[1]

        eigenvalues, eigenvectors = np.linalg.eig(cov_3D)

        sort = eigenvalues.argsort()
        # range from 0-shape[0] to allow indexing along axis 1 and 2
        idx_trick = range(eigenvalues.shape[0])

        self.eig_val1 = eigenvalues[idx_trick, sort[:,2]]
        self.eig_val2 = eigenvalues[idx_trick, sort[:,1]]
        self.eig_val3 = eigenvalues[idx_trick, sort[:,0]]

        self.eig_vec1 = eigenvectors[idx_trick, :, sort[:,2]]
        self.eig_vec2 = eigenvectors[idx_trick, :, sort[:,1]]
        self.eig_vec3 = eigenvectors[idx_trick, :, sort[:,0]]
    

    def filter_SOR(self, z_max=2.0):
        """ Compute a Statistical Outlier Removal filter using the Neighbourhood.

        Parameters
        ----------  
        z_max(Optional): float
            The maximum Z score wich determines if the point is an outlier or 
            not.
            
        Returns
        -------
        sor_filter : boolean array
            The boolean mask indicating wherever a point should be keeped or not.
            The size of the boolean mask will be the same as the number of points
            in the Neighbourhood.
            
        Notes
        -----                
        > For each point, the mean of the distances between him and his 'k' nearest 
            neighbors is computed.
        
        > The Z score of those means is computed.
        
        >  Points where the Z score is less than or more than 'z_max' are marked
            as False, in order to be trimmed.    
        
        The optional parameter (z_max) should be used in order to adjust
        the filter to the desired result.
        
        A LOWER 'z_max' value will result(normally) in a HIGHER number of points trimmed.
        """

        z_distances = zscore(np.mean(distances, axis=1), ddof=1)

        sor_filter = abs(z_distances) < z_max

        return sor_filter
    
    def radious_outlier_removal(kdtree, k, r):
    """ Compute a Radious Outlier Removal filter on the given KDTree
    
    Parameters
    ----------                        
    kdtree: scipy's KDTree instance
        The KDTree's structure which will be used to
        compute the filter.
        
    k: int
        The number of nearest neighbors wich will be used to estimate the 
        mean distance from each point to his nearest neighbors.
        
    r: float
        The radius of the sphere with center on each point and where the filter
        will look for the required number of k neighboors.    
        
    Returns
    -------
    ror_filter : boolean array
        The boolean mask indicating wherever a point should be keeped or not.
        The size of the boolean mask will be the same as the number of points
        in the KDTree.
        
    Notes
    -----
    > The filter computes the distances between each point and his 'k' nearest 
        neighbors.
        
    > The distances exceeding the given 'r' are marked as inf.
    
    > The points having any inf distance are marked as False, in order to be
        trimmed.
    
    The 2 parameters (k and r) should be used in order to adjust the filter to
    the desired result.
    
    A HIGHER 'k' value will result(normally) in a HIGHER number of points trimmed.
    
    A LOWER 'r' value will result(normally) in a HIGHER number of points trimmed.
    
    """
    
    distances, i = kdtree.query(kdtree.data, k=k, distance_upper_bound=r, n_jobs=-1) 
    
    ror_filter = np.any(np.isinf(distances), axis=1)
    
    return ror_filter


        

