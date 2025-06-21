
# we use this block so that we don't spam the console of whoever runs the install

install(CODE "message(\"Copying Amber data...\")
file(COPY ${CMAKE_CURRENT_SOURCE_DIR} DESTINATION \$ENV{DESTDIR}\${CMAKE_INSTALL_PREFIX}\)" COMPONENT Data)

if(NOT (HOST_WINDOWS OR TARGET_WINDOWS))
	installtime_create_symlink(dat/leap/cmd/leaprc.protein.ff12polL dat/leap/cmd/leaprc.protein.ff12pol Data)
endif()
