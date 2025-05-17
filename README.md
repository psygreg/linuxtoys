# linuxtoys
A collection of tools for Linux in a user-friendly way.

## Usage
- Install the proper package for your operating system from [Releases](https://github.com/psygreg/linuxtoys/releases) and run it from the applications menu.
- Any artifacts it uses will be saved in your home directory, and you can delete them after use.

## Building from source
### .deb package
This will require `debuild`, obtained from the `devscripts` package..

- Open terminal on `linuxtoys-deb/linuxtoys-1.2`
- Run `debuild -S` for .changes file or `debuild -us -uc` for a .deb package.
