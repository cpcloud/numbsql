# Release Notes

## [5.1.1](https://github.com/cpcloud/numbsql/compare/v5.1.0...v5.1.1) (2022-07-22)


### Bug Fixes

* **deps:** update dependency numpy to v1.22.0 [security] ([638180a](https://github.com/cpcloud/numbsql/commit/638180a58d5c79803106c2b71fe8737e26539f8c))

# [5.1.0](https://github.com/cpcloud/numbsql/compare/v5.0.2...v5.1.0) (2022-01-14)


### Features

* support python 3.10 ([dd916e7](https://github.com/cpcloud/numbsql/commit/dd916e78040b3d3dfe263d6452c5ce20d2d8fbe4))

## [5.0.2](https://github.com/cpcloud/numbsql/compare/v5.0.1...v5.0.2) (2022-01-14)


### Bug Fixes

* **deps:** update dependency numba to >=0.53,<0.56 ([14f0d92](https://github.com/cpcloud/numbsql/commit/14f0d9223f8ac81a08aeda3bfa134f79d530c9a1))

## [5.0.1](https://github.com/cpcloud/numbsql/compare/v5.0.0...v5.0.1) (2022-01-13)


### Bug Fixes

* **deps:** update dependency llvmlite to >=0.36,<0.39 ([7d0097e](https://github.com/cpcloud/numbsql/commit/7d0097e3dad46adf92d8fe8fb478c9eb64df74da))

# [5.0.0](https://github.com/cpcloud/numbsql/compare/v4.0.6...v5.0.0) (2022-01-08)


### Bug Fixes

* bump minimum version of numpy ([8704260](https://github.com/cpcloud/numbsql/commit/870426059e90b2578e3fcc89a0a9fac1e2b20013))


### BREAKING CHANGES

* Upgrade to numpy >=1.21

## v4.0.6 (2021-12-20)
### Fix
* Support more versions of numba/llvmlite ([`fa9a5a9`](https://github.com/cpcloud/numbsql/commit/fa9a5a9682f9d3e3511e03f9f6db04c9a44ff357))

## v4.0.5 (2021-12-19)
### Fix
* Correct the build author ([`bd7432b`](https://github.com/cpcloud/numbsql/commit/bd7432b4897faf3d5dddbde158d1618d7911b0be))

## v4.0.4 (2021-12-09)
### Fix
* **deps:** Bump to numba 0.54.1 ([`672c896`](https://github.com/cpcloud/numbsql/commit/672c8966fedfc354a0e20c9f7cd92fb96f6b3827))

## v4.0.3 (2021-12-09)
### Fix
* Try using System.B ([`aa89b32`](https://github.com/cpcloud/numbsql/commit/aa89b3202b2a621a77f30b56618076391d30ee1e))
* **sqlite:** Try to load libSystem.dylib on macos, in place of libc ([`f48bb2b`](https://github.com/cpcloud/numbsql/commit/f48bb2b55dec12a4ca4eda9c6a3b91b120f2350e))

## v4.0.2 (2021-09-23)
### Fix
* **deps:** Enable poetry2nix ([`c3c9bfc`](https://github.com/cpcloud/numbsql/commit/c3c9bfc0155448f8eac24ddfddb48e4068cf893f))

## v4.0.1 (2021-09-19)
### Fix
* **deps:** Llvmlite: 0.36 -> 0.37, numba: 0.53 -> 0.54 ([`3612ce8`](https://github.com/cpcloud/numbsql/commit/3612ce8bb1ed26c006dd8adcf9324a466c8c3bd7))
* **deps:** Bump llvm to 11 ([`bcbd77d`](https://github.com/cpcloud/numbsql/commit/bcbd77deb717ee6ac90ffcc4b956e2c6d259d78a))

## v4.0.0 (2021-08-31)
### Breaking
* The library was renamed from slumba to numbsql  ([`b7a852f`](https://github.com/cpcloud/numbsql/commit/b7a852f4c7a9c103583e01a6275d0ad0dc8929bd))

### Documentation
* Add some numbaext docs ([`b6bfec0`](https://github.com/cpcloud/numbsql/commit/b6bfec0c6b1926dc08bfde478a45a07a19f3b9a0))
* Remove invalid comment ([`3db321d`](https://github.com/cpcloud/numbsql/commit/3db321d696f4383b39ad012bf34442bef58d2bd0))

## v3.1.0 (2021-08-25)
### Feature
* Support strings in scalar udfs but not in udafs ([`fe03e2f`](https://github.com/cpcloud/slumba/commit/fe03e2f97cdf0c383e9a09f529ef6425cdd95c0f))
* **strings:** Add support for reading strings ([`b6d74cb`](https://github.com/cpcloud/slumba/commit/b6d74cb13bdbec956d6d300166fddcaa70ff8687))

## v3.0.0 (2021-08-24)
### Feature
* **api:** Refactor api to use type annotations entirely ([`164a01a`](https://github.com/cpcloud/slumba/commit/164a01ac0232a956b70a7a387805cf38d811d3ac))

### Breaking
* Type annotations must now be used to define both scalar and aggregate functions  ([`164a01a`](https://github.com/cpcloud/slumba/commit/164a01ac0232a956b70a7a387805cf38d811d3ac))

### Documentation
* More readme docs ([`48784b4`](https://github.com/cpcloud/slumba/commit/48784b499f214179124372ba83e5cba4afc36b5d))

## v2.0.0 (2021-08-22)
### Fix
* Return a new ref instead of a borrowed one ([`b9b3730`](https://github.com/cpcloud/slumba/commit/b9b37304555189f6fcbab5ebe1c0cdc658f13c86))
* Add missing exceptions.py module ([`5a1bfe0`](https://github.com/cpcloud/slumba/commit/5a1bfe0890a01f28658c8960ff5c8b9056760de5))
* Revert mypy ([`2ee28ca`](https://github.com/cpcloud/slumba/commit/2ee28cacfa5874f6b86a1457cb8a6d875c036aa5))
* Safely decref the pyobject that we use to store the state of agg initialization ([`fc70f1d`](https://github.com/cpcloud/slumba/commit/fc70f1d0038ef7eb2f529f5c7c5aeb57eb54e9da))
* Use reset_init in finalize to indicate that the next step call should reinit ([`3dc3d54`](https://github.com/cpcloud/slumba/commit/3dc3d5420e7cf6acd301170444d5a4746de54f97))
* Actually run constructors ([`8f02a99`](https://github.com/cpcloud/slumba/commit/8f02a99b42bb4cccfeae7c2851d70f8f4160b205))
* **udaf:** Compile __init__ functions ([`95fae29`](https://github.com/cpcloud/slumba/commit/95fae2952ee64b306c85246fe9b1aa21635d575e))

### Breaking
* run constructors, which previously were not being called  ([`8f02a99`](https://github.com/cpcloud/slumba/commit/8f02a99b42bb4cccfeae7c2851d70f8f4160b205))

### Documentation
* Add some docs, comments and fix types ([`3f476bf`](https://github.com/cpcloud/slumba/commit/3f476bfcdf4415df3600a27f53a70f4c99262826))
* Comment more on how byref works ([`4ed4cf0`](https://github.com/cpcloud/slumba/commit/4ed4cf0bc71cc34908bb0117f8a8ca213962f50c))

### Performance
* Tell mypy to ignore tests because it's way too slow ([`86a8b62`](https://github.com/cpcloud/slumba/commit/86a8b626f73794248f5e245ac57f9669734600a2))

## v1.3.0 (2021-08-17)
### Feature
* Add limited support for strings ([`13ed405`](https://github.com/cpcloud/slumba/commit/13ed4054a04eb2d3649bb56ada450821f30b6596))

## v1.2.2 (2021-08-17)
### Fix
* **numbaext:** Fix error message when encountering NULL values ([`b24ddd8`](https://github.com/cpcloud/slumba/commit/b24ddd863a9d29b7a3737e89c8dbb8df47fd9a5f))

## v1.2.1 (2021-08-16)
### Fix
* Raise an exception when a null is passed into a function that doesn't accept it ([`2304ef1`](https://github.com/cpcloud/slumba/commit/2304ef1f8b2f1691cd0686d895ef969348f9cc62))

## v1.2.0 (2021-08-15)
### Feature
* **shim:** Remove C++ shim ([`8e7207a`](https://github.com/cpcloud/slumba/commit/8e7207a8b4446a3f5d121a9cd68a384b5edce3cf))

### Fix
* **ci:** Checkout with the same token ([`89e145b`](https://github.com/cpcloud/slumba/commit/89e145bb12baed71ef6d690e38c66a7e3160638c))
* **ci:** Publish with PAT instead of the default github token ([`dd1137f`](https://github.com/cpcloud/slumba/commit/dd1137f38bfed4cf00359bcb597beda739657133))
* **ci:** Remove display of sqlite version on windows ([`fa91171`](https://github.com/cpcloud/slumba/commit/fa911717d9c9f87570fb64ed3d20d131074facc4))
* Back to conda and show sqlite3 versions ([`bb0d6d6`](https://github.com/cpcloud/slumba/commit/bb0d6d649fc77e270ca361734f4c0e6bac9ddc8d))
* Make sure tokens are set correctly in release step ([`c69cb43`](https://github.com/cpcloud/slumba/commit/c69cb430d5c56a19b95129a0c77ad7a6615cca37))

## v1.1.17 (2021-08-14)
### Fix
* Make unset a parameter ([`e7e5e60`](https://github.com/cpcloud/slumba/commit/e7e5e609a3e313acdbbc5f24b15c408130755be6))

## v1.1.16 (2021-08-14)
### Fix
* Use poetry config for tokens ([`e41647e`](https://github.com/cpcloud/slumba/commit/e41647e729df9b11cf4d9cc712225a1249b796dd))

## v1.1.15 (2021-08-14)
### Fix
* Don't try to publish on PRs ([`a8995d0`](https://github.com/cpcloud/slumba/commit/a8995d03a5f6e0655ca1740bd50a55690475888b))
* **ci:** Checkout the right tag ([`a0119a2`](https://github.com/cpcloud/slumba/commit/a0119a2689ae56021e3225bd872debb5b97dde18))

## v1.1.14 (2021-08-14)
### Fix
* Fix poetry publishing ([`0a775dc`](https://github.com/cpcloud/slumba/commit/0a775dc9a26b7ec3b3e3451bbaa16a6078e2e75b))

## v1.1.13 (2021-08-14)
### Fix
* Try publishing on pypi ([`584337c`](https://github.com/cpcloud/slumba/commit/584337c3197ed586959300835b3deabe3a08229d))

## v1.1.12 (2021-08-14)
### Fix
* Fix library paths on windows ([`82e0e97`](https://github.com/cpcloud/slumba/commit/82e0e9757bedb3112ceff4ba34d6d1fc7008d58a))
* Publish with poetry instead of twine ([`4101223`](https://github.com/cpcloud/slumba/commit/41012233fad34208c12ad493a05bc7f3bf070381))

## v1.1.11 (2021-08-14)
### Fix
* Fix publishing ([`1ad3353`](https://github.com/cpcloud/slumba/commit/1ad33538ac13601804670f8d9c4342bd78cab7d5))

## v1.1.10 (2021-08-14)
### Fix
* Don't try to anticipate the version ([`4e326c3`](https://github.com/cpcloud/slumba/commit/4e326c37bf781f3cc6d727326acac6334955b525))
* Get the new version tag directly ([`960b65a`](https://github.com/cpcloud/slumba/commit/960b65a48684a0a9220ba5f0523bb2dd6b3969bf))

## v1.1.9 (2021-08-14)
### Fix
* Forget about using fromJSON ([`27e0590`](https://github.com/cpcloud/slumba/commit/27e0590e6bcff7c10ba33049b2b862bbd927379e))

## v1.1.8 (2021-08-14)
### Fix
* Get the correct ref from the release step ([`e771857`](https://github.com/cpcloud/slumba/commit/e77185756e6a28fe766cba3114614e328fb43b93))

## v1.1.7 (2021-08-14)
### Fix
* Fix publishing again ([`0dbf1d0`](https://github.com/cpcloud/slumba/commit/0dbf1d061c140bee55ce7f6cb1e1773135725b2d))

## v1.1.6 (2021-08-14)
### Fix
* Try all the events ([`5b02218`](https://github.com/cpcloud/slumba/commit/5b0221857f8da6244d285ee1c83fb6ebaaa208c2))

## v1.1.5 (2021-08-14)
### Fix
* Publish on released event ([`4e1d885`](https://github.com/cpcloud/slumba/commit/4e1d885656f56c7beed0a37202f430c983f0c236))

## v1.1.4 (2021-08-14)
### Fix
* Don't upload to releases ([`4f8af98`](https://github.com/cpcloud/slumba/commit/4f8af982831d71bf459c457ca5a4ce0efaa3d670))

## v1.1.3 (2021-08-14)
### Fix
* Publish on a published release event ([`3067a56`](https://github.com/cpcloud/slumba/commit/3067a5611fa8170112abe41e951441b378d33d98))

## v1.1.2 (2021-08-14)
### Fix
* Fix publishing on pypi ([`52876ab`](https://github.com/cpcloud/slumba/commit/52876ab065787d254f1d02cc1e2f609e6ea599ec))

## v1.1.1 (2021-08-13)
### Fix
* Feed the tagged commit through ([`2b74cb6`](https://github.com/cpcloud/slumba/commit/2b74cb634ddd2d2e6112b495f1c78ae4a15c644e))
* Only build wheels ([`8b3ae90`](https://github.com/cpcloud/slumba/commit/8b3ae901b29c6a749fdc867bd5d0185563d19679))

## v1.1.0 (2021-08-13)
### Feature
* Add __version__ to slumba/__init__.py ([`86fbcdd`](https://github.com/cpcloud/slumba/commit/86fbcdd0122495a5b0a55c3c57913b9dc34c5bae))

## v1.0.6 (2021-08-13)
### Fix
* Release them all ... again ([`fc90f22`](https://github.com/cpcloud/slumba/commit/fc90f22278bbffd8261e0cee562af15891785dbb))
* Release just one ([`0794a7b`](https://github.com/cpcloud/slumba/commit/0794a7b7ca6663265a64f9f1e6c01ec81e6a5b41))

## v1.0.5 (2021-08-13)
### Fix
* Fix workflow ([`9f48cb4`](https://github.com/cpcloud/slumba/commit/9f48cb4dfbdb4ef0b6705f534680b8b5de7b8670))
* Try to run with every python version separately ([`6c2fd69`](https://github.com/cpcloud/slumba/commit/6c2fd69a4bcfa278079e72c6c098121936901cef))

## v1.0.4 (2021-08-13)
### Fix
* Install the right library and invoke it correctly ([`0d91168`](https://github.com/cpcloud/slumba/commit/0d91168ace122c5d513f8baa90466cac2335a18c))
* Fix semantic release package name on install ([`68b8031`](https://github.com/cpcloud/slumba/commit/68b8031ab0eb2b3df6a21023d557491f71f569cf))
* Actually install semantic release ([`f82319b`](https://github.com/cpcloud/slumba/commit/f82319b536ba99b46281f40add02d23981dc8ea8))
* Fix setup python keys ([`55c9bd9`](https://github.com/cpcloud/slumba/commit/55c9bd98da187ec07d2ee2abd42b4213b87d8425))
* Checkout and fix name ([`8931ecd`](https://github.com/cpcloud/slumba/commit/8931ecde6dcf62a7a91544dc76f711ffef18bd4d))
* Rework semantic release ([`c4f6fa8`](https://github.com/cpcloud/slumba/commit/c4f6fa886c94489d56a766018dedcd2e643428eb))

## v1.0.3 (2021-08-13)
### Fix
* **pypi:** Leave the license classifier out for now ([`6f685a5`](https://github.com/cpcloud/slumba/commit/6f685a50b652eeade8d8b72fd6b292839b0e17d4))

## v1.0.2 (2021-08-13)
### Fix
* Start uploading to pypi ([`b3b9ba1`](https://github.com/cpcloud/slumba/commit/b3b9ba1f50210a6d617d0d09bf80077aa37fb902))

## v1.0.1 (2021-08-13)
### Fix
* **setup:** Include pkg-config in the build ([`1b1de91`](https://github.com/cpcloud/slumba/commit/1b1de918f59b7a68851541ee68c00e10dc4266fd))
* Release depends on windows passing too ([`650bd88`](https://github.com/cpcloud/slumba/commit/650bd88694a5e8168e342f4b1e2d346f36a4ce86))
* Workaround pinned pip version in poetry2nix, document why ([`e1bba5d`](https://github.com/cpcloud/slumba/commit/e1bba5d71b5d53a4b34c41a9507e63d0ba8be9fa))
* Add sqlite to build dependencies ([`8aa16ba`](https://github.com/cpcloud/slumba/commit/8aa16bacf6b5134185bcbde55d47626a041fba1e))
* Add sqlite to build deps ([`7e73dd0`](https://github.com/cpcloud/slumba/commit/7e73dd020618a458b5144ba0da9bdfd37b3ea21f))
* Add missing sqlite3 dependency for building cslumba extension ([`691545b`](https://github.com/cpcloud/slumba/commit/691545b1df5b5924a8a110c88e3dcd3dc0298f2f))
* **dev:** Fix invocation of sqlite ([`931d545`](https://github.com/cpcloud/slumba/commit/931d54599e3205ce137c49fff5b4df17f849c915))
* Fix poetry2nix bug ([`e509e8e`](https://github.com/cpcloud/slumba/commit/e509e8e0baa5f3ca057ec9fbcd5502078c17f6b1))
* Fix the pointer type of the connection pointer ([`e4faf33`](https://github.com/cpcloud/slumba/commit/e4faf339172e2a79fc75ffe70e742601715d77ec))

### Documentation
* Add CHANGELOG.md template ([`b271165`](https://github.com/cpcloud/slumba/commit/b2711653cb7ad4cb721db2fd62a006e125ff094f))
* Add readme to pyproject.toml and replace email ([`c61c670`](https://github.com/cpcloud/slumba/commit/c61c67031c925638e15a9418cb919a2766845c07))
