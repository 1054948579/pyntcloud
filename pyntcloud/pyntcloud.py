#  HAKUNA MATATA

"""
PyntCloud class
"""

import numpy as np
import pandas as pd

from scipy import spatial

from .filters.kdtree_filters import radious_outlier_removal, statistical_outilier_removal
from .filters.other_filters import pass_through
from .io.npz import read_npz, write_npz
from .io.obj import read_obj, write_obj
from .io.pcd import read_pcd, write_pcd
from .io.ply import read_ply, write_ply

DESCRIPTION = """\
\tPyntCloud
\t=========\n
{} points with {} scalar fields
{} faces
{} kdtrees
{} octrees
{} voxelgrids
Centroid: {}, {}, {}\n
Other attributes:{}        
"""


class PyntCloud(object):
    """ A Pythonic Point Cloud
    """
    
    def __init__(self, **kwargs):  

        if "points" not in kwargs:
            raise ValueError("There must be a 'points' key in the kwargs")

        elif not set(['x', 'y', 'z']).issubset(kwargs["points"].columns):
            raise ValueError("Points must have x, y and z coordinates")

        self.kdtrees = []
        self.octrees = []
        self.voxelgrids = []

        for key in kwargs:
            if "kdtree" in key:
                self.kdtrees.append(kwargs[key])
            elif "octree" in key:
                self.octrees.append(kwargs[key])
            elif "voxelgrid" in key:
                self.voxelgrids.append(kwargs[key])
            else:
                setattr(self, key, kwargs[key])
        
        self.centroid = np.mean(self.points[["x", "y", "z"]].values, axis=0)
        

    def __repr__(self):

        others = []
        for name in self.__dict__:
            if name not in ["_PyntCloud__points", "mesh", "kdtrees", "octrees", "voxelgrids", "centroid"]:
                others.append("\n\t " + name + ": " + str(type(name)))
        others = "".join(others)

        try:
            n_faces = len(self.mesh)
        except AttributeError:
            n_faces = 0

        return DESCRIPTION.format(
                                    len(self.points), len(self.points.columns),
                                    n_faces,
                                    len(self.kdtrees),
                                    len(self.octrees),
                                    len(self.voxelgrids),
                                    self.centroid[0], self.centroid[1], self.centroid[2],
                                    others                                    
                                    )


    @property
    def points(self):
        return self.__points

    
    @points.setter
    def points(self, df):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Points argument is not a DataFrame")
        self.__points = df

             
    @classmethod
    def from_file(cls, filename):
        """ Extracts data from file and constructs a PyntCloud with it
        Parameters
        ----------
        filename : str
            Path to the file from wich the data will be readed

        Returns
        -------
        PyntCloud : object
            PyntCloud's instance, containing all elements in the file stored as
            PyntCloud's attributes

        """
        formats_readers = {"NPZ": read_npz,
                           "OBJ": read_obj,
                           "PCD": read_pcd,
                           "PLY": read_ply
                          }
        
        ext = filename.split(".")[-1].upper()
        if ext not in formats_readers.keys():
            raise ValueError("Unsupported file format; supported formats are: " 
                            + "  ".join(formats_readers.keys()))
        else:
            return PyntCloud( **formats_readers[ext](filename) )


    def add_normals(self, neighbors, element='vertex', and_curvature=True):
        """
        """

        cloud = getattr(self, element)

        #: compute PCA over each group of K neighbors
        eigenvalues, eigenvectors = np.linalg.eig(vCov(neighbors))

        #: get the indices of the smallest eigenvector
        sort = eigenvalues.argsort()[:,0]

        #: create an empty array
        normals = np.empty(eigenvalues.shape)

        #: fill with the correspondig smallest eigenvector
        #: separating to avoid memory break
        normals[sort == 0] = eigenvectors[sort == 0][:,:,0]
        normals[sort == 1] = eigenvectors[sort == 1][:,:,1]
        normals[sort == 2] = eigenvectors[sort == 2][:,:,2]

        if and_curvature:
            eigenvalues.sort()

            #: get curvature by divinging the lowest eigenvalue by the sum of all the eigenvalues
            curvature = eigenvalues[:,0] / np.sum(eigenvalues, axis=1)

            cloud['curvature_' + str(neighbors.shape[1])] = curvature

        cloud['nx'] = normals[:,0]
        cloud['ny'] = normals[:,1]
        cloud['nz'] = normals[:,2]

        setattr(self, element, cloud)


    def orient_normals(self, view_points, element='vertex'):

        cloud = getattr(self, element)

        centroids = cloud[['centroid_x','centroid_y','centroid_z']].drop_duplicates().values

        remain_idx = list(range(centroids.shape[0]))

        view_rays = np.zeros_like(centroids, dtype=np.float32)



    def add_inclination(self, element='vertex', degrees=True):
        """ Adds inclination (with respect to z-axis) values to PyntCloud.element

        Parameters
        ----------
        degrees(Optional) : bool
            Set the oputput inclination units:
                If True(Default) set units to degrees.
                If False set units to radians.

        Notes
        -----
        This function expects the PyntCloud to have a numpy structured array
        with normals x,y,z values (correctly named) as the corresponding element
        atribute.

        """

        cloud = getattr(self, element)

        angle = np.arccos(cloud['nz'].values)

        if degrees:

            cloud = cloud.assign(inclination_deg = np.rad2deg(angle))

        else:

            cloud = cloud.assign(inclination_rad = angle)

        setattr(self, element, cloud)


    def add_orientation(self, element='vertex', degrees=True):
        """ Adds orientation (with respect to y-axis) values to PyntCloud.element

        Parameters
        ----------
        degrees(Optional) : bool
            Set the oputput orientation units:
                If True(Default) set units to degrees.
                If False set units to radians.

        Notes
        -----
        This function expects the PyntCloud to have a numpy structured array
        with normals x,y,z values (correctly named) as the corresponding element
        atribute.

        """

        cloud = getattr(self, element)

        nx = cloud['nx'].values
        ny = cloud['ny'].values

        angle = np.arctan2(nx,ny)

        #: convert (-180 , 180) to (0 , 360)
        angle[(np.where(angle < 0))] = (2*np.pi) + angle[(np.where(angle < 0))]

        if degrees:

            cloud['orientation_deg'] = np.rad2deg(angle)

        else:

            cloud['orientation_rad'] = angle

        setattr(self, element, cloud)


    def add_zscore_of(self, scalar_field, element='vertex'):
        """ Adds the Standard score values of the given SF to PyntCloud.element

        Parameters
        ----------
        scalar_field : str
            The desired scalar fields from wich we want to estimate the Standard scores.

        Notes
        -----
        This function expects the PyntCloud to have a numpy structured array
        with the given Scalar Field as the corresponding element atribute.

        This function will add a new scalar field named as the original scalar
        field with a 'Z' on the front.

        """

        cloud = getattr(self, element)

        v = cloud[scalar_field]

        cloud['Z_' + scalar_field] = (v - v.mean()) / v.std(ddof=0)

        setattr(self, element, cloud)


    def add_dist_to_point(self, point, element='vertex', metric='euclidean'):
        """ Adds the distance between PyntCloud.vertex's points and the given point

        Parameters
        ----------
        point: array
            The point to wich the distances will be computated.It must be given
            as an array with 3 elements, corresponding to the X,Y,Z coordinates.

        metric(Optional): str
            The "type" of the distance. See: "scipy.spatial.distance.cdist" docs
            for more information.

        Notes
        -----
        The corresponding distance will be added as a new SF for every point
        in PyntCloud.element.

        """

        cloud = getattr(self, element)

        #: store the point formatted to use the scipy's cdist
        origin = np.array([point])

        coords = cloud[['x','y','z',]]

        #:get the coordiantes of the point as str in order to name the SF
        name = ','.join(str(e) for e in point)

        distance = spatial.distance.cdist(origin, coords, metric).flatten()

        cloud['to:' + name] = distance

        setattr(self, element, cloud)


    def add_rgb_intensity(self, element='vertex'):
        """ Adds Red, Blue and Green intensity values to PyntCloud.vertex

        Notes
        -----
        This function expects the PyntCloud to have a numpy structured array
        with rgb values (correctly named) as the corresponding vertex atribute.

        """
        cloud = getattr(self, element)

        r = cloud['red'].values.astype(np.float, copy=False)
        g = cloud['green'].values.astype(np.float, copy=False)
        b = cloud['blue'].values.astype(np.float, copy=False)

        rgb = r + g + b

        cloud['Ri'] = r / rgb
        cloud['Gi'] = g / rgb
        cloud['Bi'] = b / rgb


    def add_hsv(self, element='vertex'):
        """ Adds the values obtained from conversion RGB-HSV to PyntCloud.vertex

        Notes
        -----
        This function expects the PyntCloud to have a numpy structured array
        as PyntCloud.vertex attribute, with valid RGB values correctly named
        ('red', 'green', 'blue')

        The corresponding HSV values will be added as 3 news SF for every point
        in PyntCloud.vertex

        """

        cloud = getattr(self, element)

        raise NotImplementedError


    def add_relative_luminance(self, element='vertex'):
        """ Adds the relative luminance values(conversion RGB-GRAY) to PyntCloud.element

        Parameters
        ----------
        element(Optional) : str
            The PyntCloud's element where the function will look for RGB values
            in order to compute the relative luminance.

        Notes
        -----
        This function expects the PyntCloud to have a numpy structured array
        as PyntCloud.vertex attribute, with valid RGB values correctly named
        ('red', 'green', 'blue')

        The corresponding realtive_luminance values will be added as 1 new SF
        for every point in PyntCloud.element

        """

        cloud = getattr(self, element)

        #: luminosity function coefficients
        coef = np.array([0.2125, 0.7154, 0.0721])

        rgb = cloud[['red','green','blue']]

        gray = np.einsum('ij, j', rgb, coef)

        cloud['Relative_Luminance'] = gray

        setattr(self, element, cloud)


    def get_Octree(self, n=1, element='vertex'):
        """ Computes the Octree of the given PyntCloud.element

        Parameters
        ----------

        n(Optional): int
            The number of the maximum level of subdivision.

        element(Optional): str
            The PyntCloud.element where the function will search for the xyz
            coordinates to build the octree.

        Returns
        -------
        octree : pyntcloud's VoxelGrid instance
            The Octree's structure of xyz coordinates of the given element.

        """
        raise NotImplementedError


    def get_KDTree(self, scalar_fields, element='vertex', and_set=True):
        """ Computes the KDTree of the given PyntCloud.element's scalar fields.

        Parameters
        ----------
        scalar_fields: list[str]
            The names of the scalar fields.

         element(Optional): str
            The PyntCloud's element where the function will look for the scalar
            fields in order to compute the KDTree. Default: PyntCloud.vertex.

        and_set(Optional): bool
            If True(Default): set a new attribute with the computed element
            If False: return the computed element

        Returns
        -------
        kdtree : scipy's KDTree instance
            The KDTree's structure of the given scalar fields.

        """

        cloud = getattr(self, element)

        stacked = cloud[scalar_fields]

        kdtree = spatial.cKDTree(stacked)

        if and_set:

            setattr(self, 'kdtree', kdtree)

        else:

            return kdtree


    def get_k_neighbors(self, k, kdtree=None, element='vertex', and_set=True):
        """ Computes the K nearest neighbors of the PyntCloud.element's KDTree

        Parameters
        ----------
        k: int
            The number of nearest neighbors that will be computed for each point.

        kdtree(Optional): scipy's KDTree instance
            The KDTree's structure which will be used to compute the neighbors.
            If no KDTree is supplied, it will be computed using the x,y,z scalar
            fields of the given element.

        element(Optional): str
            The PyntCloud's element from where the x,y,z scalar fields will be
            used if no KDTree is supplied.

        and_set(Optional): bool
            If True(Default): set a new attribute with the computed element
            If False: return the computed element

        Returns
        -------
        neighbors : array
            The array containing the K neighbors for each point.
            With shape: (N, k, 3). Where:
                N is the number of points in the PyntCloud.element.
                k the number of neighbors finded for each point.
                And the last dimension contains the XYZ  coordinates for each of
                    those 'k' neighbors.

        """

        if not kdtree:

            kdtree = self.get_KDTree('x','y','z', element=element)

        xyz = self.kdtree.data

        d, i = self.kdtree.query(xyz, k=k, n_jobs=-1)

        #: group the neighbors in one array
        neighbors = xyz[i]

        if and_set:

            setattr(self, 'neighbors_'+str(k), neighbors)

        else:

            return neighbors


    def get_centroid(self, element='vertex', and_set=True):
        """ Computes the centroid of the given PyntCloud.element

        Parameters
        ----------
        element: str
            The PyntCloud's element from wich we want to compute the centroid.

        Returns
        -------
        centroid : array
            The (x,y,z) coordiantes of the PyntCloud.element's centroid.

        and_set(Optional): bool
            If True(Default): set a new attribute with the computed element
            If False: return the computed element

        Notes
        -----
        This function expects the PyntCloud to have the elemenent as a numpy
        structured array, with (x,y,z) coordenates correctly named.

        """

        cloud = getattr(self, element)

        xyz = cloud[['x','y','z']]

        centroid = np.mean(xyz, axis=0)

        if and_set:

            setattr(self, 'centroid', centroid)

        else:

            return centroid


    def get_transf(self, element='vertex', and_set=True):
        """ Get a transformer matrix from the given element

        Parameters
        ----------
         element(Optional): str
            The PyntCloud's element where the function will look for the scalar
            fields in order to compute the transformer matrix.

        and_set(Optional): bool
            If True(Default): set a new attribute with the computed element
            If False: return the computed element

        Returns
        -------
        transf : (N,4) array
            The transformer matrix of the element.


        """
        cloud = getattr(self, element)

        transf = cloud[['x','y','z']]

        transf = np.c_[ transf, np.ones(transf.shape[0]) ]

        if and_set:

            setattr(self, 'transf', transf)

        else:

            return transf


    def clean_SOR(self, kdtree, element='vertex', k=8, z_max=2 ):
        """ Applies a Statistical Outlier Removal filter on the given KDTree.

        Parameters
        ----------
        kdtree: scipy's KDTree instance
            The KDTree's structure which will be used to
            compute the filter.

        element(Optional): str
            The PyntCloud.element where the fillter will be apllied.

        k(Optional): int
            The number of nearest neighbors wich will be used to estimate the
            mean distance from each point to his nearest neighbors.
            Default : 8

        z_max(Optional): int
            The maximum Z score wich determines if the point is an outlier or
            not.

        Notes
        -----
        Check the filter_SOR function for more information.

        """
        cloud = getattr(self, element)

        filtered = statistical_outilier_removal(kdtree, k, z_max)

        setattr(self, element, cloud[filtered])


    def clean_ROR(self, kdtree,  k, r, element='vertex'):
        """ Applies a Radious Outlier Removal filter on the given KDTree.

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

        Notes
        -----
        Check the filter_ROR function for more information.

        """

        cloud = getattr(self, element)

        filtered = radious_outlier_removal(kdtree, k, r)

        setattr(self, element, cloud[filtered])


    def clean_PT(self, element='vertex', min_x=-np.inf, max_x=np.inf,
                 min_y=-np.inf, max_y=np.inf, min_z=-np.inf, max_z=np.inf):
        """ Applies a Pass Through filter on the given element

        Parameters
        ----------
        element(Optional) : str
            The sPyntCloud's element where the function will look for the xyz
            coordinates in order to aplly the filter. Default: vertex

        Notes
        -----
        The function expects the element to have the scalar fields x,y and z
        correctly named.

        Check the filter_BB function for more information.
        """

        cloud = getattr(self, element)

        points  = cloud[['x','y','z']]

        filtered = pass_through(points, min_x, max_x, min_y, max_y, min_z, max_z)

        setattr(self, element, cloud[filtered])


    def octree_subsample(self, octree, element='vertex'):
        """ Subsamples the point cloud based on the given octree

        Parameters
        ----------
        octree : pyntcloud's VoxelGrid instance
            The Octree's structure that will be used to subsamble the point cloud

        Notes
        -----
        The function will keep only 1 point per octree's voxel, by searching in
        all the points inside an octree's voxel for the point that is nearer to
        the octree's voxel centroid.

        """

        cloud = getattr(self, element)

        cloud = pd.concat([cloud, octree.structure], axis=1)

        v2 = cloud[['x','y','z']].as_matrix()

        v1 = cloud[['centroid_x','centroid_y','centroid_z']].as_matrix()

        cloud['distances'] = np.linalg.norm(v2 - v1, axis=1)

        cloud = cloud.loc[cloud.groupby(['voxel_x','voxel_y','voxel_z'])['distances'].idxmin()]

        setattr(self, element, cloud)


    def random_subsample(self, n_points, element='vertex'):
        """ Subsamples the point cloud randomly

        Parameters
        ----------
        n_points : int
            The number of points that will have the subsampled cloud.

        """

        cloud = getattr(self, element)

        setattr(self, element, cloud.sample(n_points))
        

def vCov(data, sort=True):

    diffs = data - data.mean(1,keepdims=True)

    return np.einsum('ijk,ijl->ikl',diffs,diffs) / data.shape[1]
