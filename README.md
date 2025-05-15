# linuxtoys
A collection of tools for Linux in a user-friendly way.

## Usage
- Install the proper package for your operating system from [Releases](https://github.com/psygreg/linuxtoys/releases) and run it from the applications menu.

## Building from source
### .deb package
This will require `debuild`.

- Open terminal on `linuxtoys-deb/linuxtoys-1.2`
- Run `debuild -S` for .changes file or `debuild -us -uc` for a .deb package.