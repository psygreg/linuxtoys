# Releasing an update

#### Updating the Version Number
Use the provided helper script:
```bash
python update_version.py 4.4
```

This will update both:
1. The main version file `../src/ver`
2. The fallback version in `app/update_helper.py` (if needed)

Or manually edit `../src/ver` and change the version number there.

#### Creating a Release
1. Update the version number using `update_version.py`
2. Commit the change
3. Create a new release tag on GitHub
4. The update system will automatically detect the new version
