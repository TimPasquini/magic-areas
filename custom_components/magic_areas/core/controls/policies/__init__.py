"""Policy adapter package for control-group features.

Import concrete policy symbols from their feature modules directly. Keeping this
package root lazy avoids import cycles between option defaults and individual
policy modules during Home Assistant config-flow discovery.
"""
