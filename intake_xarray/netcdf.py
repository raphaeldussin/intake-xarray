# -*- coding: utf-8 -*-
import fsspec
from distutils.version import LooseVersion
from intake.source.base import PatternMixin
from intake.source.utils import reverse_format
from .base import DataSourceMixin


class NetCDFSource(DataSourceMixin, PatternMixin):
    """Open a xarray file.

    Parameters
    ----------
    urlpath : str, List[str]
        Path to source file. May include glob "*" characters, format
        pattern strings, or list.
        Some examples:
            - ``{{ CATALOG_DIR }}/data/air.nc``
            - ``{{ CATALOG_DIR }}/data/*.nc``
            - ``{{ CATALOG_DIR }}/data/air_{year}.nc``
    chunks : int or dict, optional
        Chunks is used to load the new dataset into dask
        arrays. ``chunks={}`` loads the dataset with dask using a single
        chunk for all arrays.
    concat_dim : str, optional
        Name of dimension along which to concatenate the files. Can
        be new or pre-existing. Default is 'concat_dim'.
    path_as_pattern : bool or str, optional
        Whether to treat the path as a pattern (ie. ``data_{field}.nc``)
        and create new coodinates in the output corresponding to pattern
        fields. If str, is treated as pattern to match on. Default is True.
    storage_options: dict
        If using a remote fs (whether caching locally or not), these are
        the kwargs to pass to that FS.
    """
    name = 'netcdf'

    def __init__(self, urlpath, chunks=None, concat_dim='concat_dim',
                 xarray_kwargs=None, metadata=None,
                 path_as_pattern=True, storage_options=None, **kwargs):
        self.path_as_pattern = path_as_pattern
        self.urlpath = urlpath
        self.chunks = chunks
        self.concat_dim = concat_dim
        self.storage_options = storage_options or {}
        self._kwargs = xarray_kwargs or {}
        self._ds = None
        super(NetCDFSource, self).__init__(metadata=metadata, **kwargs)

    def _open_dataset(self):
        import xarray as xr
        url = self.urlpath
        kwargs = self._kwargs
        if "*" in url or isinstance(url, list):
            _open_dataset = xr.open_mfdataset
            if 'concat_dim' not in kwargs.keys():
                kwargs.update(concat_dim=self.concat_dim)
            if self.pattern:
                kwargs.update(preprocess=self._add_path_to_ds)
            if 'combine' not in kwargs.keys():
                kwargs.update(combine='nested')
        else:
            _open_dataset = xr.open_dataset
        url = fsspec.open_local(url, **self.storage_options)

        self._ds = _open_dataset(url, chunks=self.chunks, **kwargs)

    def _add_path_to_ds(self, ds):
        """Adding path info to a coord for a particular file
        """
        import xarray as xr
        XARRAY_VERSION = LooseVersion(xr.__version__)
        if not (XARRAY_VERSION > '0.11.1'):
            raise ImportError("Your version of xarray is '{}'. "
                "The insurance that source path is available on output of "
                "open_dataset was added in 0.11.2, so "
                "pattern urlpaths are not supported.".format(XARRAY_VERSION))

        var = next(var for var in ds)
        new_coords = reverse_format(self.pattern, ds[var].encoding['source'])
        return ds.assign_coords(**new_coords)
