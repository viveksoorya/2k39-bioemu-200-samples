
### Planning phase:
1) List out all the argument you would like to offer to the user. Adhere to standard flags where you can.

### Code essentials:
1) import argparser
2) create an object. I will call the object parser, but you can use whatever name you like. 
3) parser.add_argument('<insert-argument-or-flag>', required=<insert-boolean>, description="<add description that the user needs to read.>")
4) repeat step three for all your arguments
5) now create an other temporary object using step 6. I will call this object args.
6) args = parser.parse_args()
7) now you can access the values that will be passed by the user to your flag or argument using args.<insert-flag-without-dash>
8) Define a main function and do what you will with the extracted argument within the main
9) Then use the following conditional at the end so that the script runs only when the file is directly run, and not when it is imported:
```python
if __name__ == "__main__":
    main()
```