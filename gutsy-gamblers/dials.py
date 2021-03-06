from datetime import timedelta, datetime, date

from geopy import Point
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import (
    NumericProperty,
    ObjectProperty,
    ConfigParserProperty,
    ReferenceListProperty
)
from kivy.uix.effectwidget import EffectWidget, EffectBase
from kivy.uix.floatlayout import FloatLayout
from suntime import SunTimeException, Sun

import datahelpers

hv_blur = """
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{{
    float dt = ({} / 4.0) * 1.0 / resolution.x;
    vec4 sum = vec4(0.0);
    sum += texture2D(texture, vec2(tex_coords.x - 4.0*dt, tex_coords.y))
                     * 0.05;
    sum += texture2D(texture, vec2(tex_coords.x - 3.0*dt, tex_coords.y))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x - 2.0*dt, tex_coords.y))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x - dt, tex_coords.y))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y))
                     * 0.16;
    sum += texture2D(texture, vec2(tex_coords.x + dt, tex_coords.y))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x + 2.0*dt, tex_coords.y))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x + 3.0*dt, tex_coords.y))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x + 4.0*dt, tex_coords.y))
                     * 0.05;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - 4.0*dt))
                     * 0.05;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - 3.0*dt))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - 2.0*dt))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - dt))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y))
                     * 0.16;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + dt))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + 2.0*dt))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + 3.0*dt))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + 4.0*dt))
                     * 0.05;
    return vec4(sum.xyz, color.w);
}}
"""


# Widget element things #
class DialWidget(FloatLayout):
    """
    Speed will become a fixed value of 86400 once completed.
    Image should, i suppose, be a fixed image?
    At some point we'll need to add a tuple(?) for sunrise / sunset times.
    """
    angle = NumericProperty(0)

    config_latlon = latlon = ConfigParserProperty(
        '', 'global', datahelpers.LOCATION_LATLON, 'app', val_type=str)

    latlon_point = ObjectProperty()

    sunrise = NumericProperty()
    sunset = NumericProperty()
    sun_angles = ReferenceListProperty(sunrise, sunset)

    def on_config_latlon(self, instance, value):
        """Handler for property change event"""
        self.latlon_point = Point(value)
        self.redraw()

    def __init__(self, **kwargs):
        super(DialWidget, self).__init__(**kwargs)

        # Widget properties
        self.day_length = 86400
        self.date_increase = 1
        self.dial_size = (0.8, 0.8)
        self.date = datetime.now()

        self.midnight = (self.date + timedelta(days=1))
        self.midnight_delta = (datetime(year=self.midnight.year,
                                        month=self.midnight.month,
                                        day=self.midnight.day,
                                        hour=0, minute=0, second=0) - self.date).seconds

        # Set sunrise and sunset through reference list
        self.sun_angles = self.sun_time()

        # Shading widget
        self.dial_shading = DialEffectWidget((self.sunrise, self.sunset))
        self.add_widget(self.dial_shading)

        if self.sun_angles not in [[0, 0], [0, 360]]:
            self.sun_rise_marker = SunRiseMarker(self.sunrise)
            self.sun_set_marker = SunSetMarker(self.sunset)
            self.add_widget(self.sun_rise_marker)
            self.add_widget(self.sun_set_marker)

        self.animate_dial()
        self.clock = Clock.schedule_interval(self.redraw, self.midnight_delta)

    def animate_dial(self):
        anim = Animation(angle=359, duration=self.day_length)
        anim += Animation(angle=359, duration=self.day_length)
        anim.repeat = True
        anim.start(self)

    def redraw(self, a=None):
        # Split suntime tuple into named variables
        self.sun_angles = self.sun_time()

        # Remove widgets
        self.remove_widget(self.dial_shading)
        try:
            self.remove_widget(self.sun_rise_marker)
            self.remove_widget(self.sun_set_marker)
        except AttributeError:
            # Previous day had no sunrise/sunset, no widgets to remove
            pass

        # Shading widget
        self.dial_shading = DialEffectWidget((self.sunrise, self.sunset))
        self.add_widget(self.dial_shading)

        if self.sun_angles not in [[0, 0], [0, 360]]:
            self.sun_rise_marker = SunRiseMarker(self.sunrise)
            self.sun_set_marker = SunSetMarker(self.sunset)
            self.add_widget(self.sun_rise_marker)
            self.add_widget(self.sun_set_marker)

        # Restart the clock!
        self.clock.cancel()
        self.clock = Clock.schedule_interval(self.redraw, self.midnight_delta)

    def sun_time(self):

        sun_time = Sun(self.latlon_point.latitude, self.latlon_point.longitude)

        self.date = self.date + timedelta(days=self.date_increase)

        try:
            today_sunrise = sun_time.get_sunrise_time(self.date)
        except SunTimeException:
            if date(year=self.date.year, month=3, day=21)\
                    < self.date.date()\
                    < date(year=self.date.year, month=9, day=22):
                return 0, 360
            return 0, 0

        try:
            today_sunset = sun_time.get_sunset_time(self.date)
        except SunTimeException:
            if date(year=self.date.year, month=3, day=21)\
                    < self.date.date()\
                    < date(year=self.date.year, month=9, day=22):
                return 0, 360
            return 0, 0

        # This is *super* ugly, I'm sure we can find a more elegant way to do this
        now = datetime.utcnow() - timedelta(hours=0)
        today_sunrise = today_sunrise.replace(tzinfo=None)
        today_sunset = today_sunset.replace(tzinfo=None)

        # After Sunrise, after Sunset
        if now > today_sunrise and today_sunset:
            # Get timedelta for each
            today_sunrise = now - today_sunrise
            today_sunset = now - today_sunset

            # Convert timedelta into minutes and round
            today_sunrise = round(today_sunrise.seconds / 60)
            today_sunset = round(today_sunset.seconds / 60)

            # Convert minutes into angles
            today_sunrise = today_sunrise * 0.25
            today_sunset = today_sunset * 0.25

        # Before Sunrise, after Sunset
        elif now < today_sunrise and today_sunset:
            today_sunrise = today_sunrise - now
            today_sunset = today_sunset - now

            today_sunrise = round(today_sunrise.seconds / 60)
            today_sunset = round(today_sunset.seconds / 60)

            today_sunrise = 360 - (today_sunrise * 0.25)
            today_sunset = 360 - (today_sunset * 0.25)

        # After Sunrise, before Sunset
        else:
            today_sunrise = now - today_sunrise
            today_sunset = today_sunset - now

            today_sunrise = round(today_sunrise.seconds / 60)
            today_sunset = round(today_sunset.seconds / 60)

            today_sunrise = today_sunrise * 0.25
            today_sunset = 360 - (today_sunset * 0.25)

        return today_sunrise, today_sunset

    def on_angle(self, item, angle):
        if angle == 359:
            item.angle = 0
            self.redraw()


class DoubleVision(EffectBase):
    size = NumericProperty(4.0)

    def __init__(self, *args, **kwargs):
        super(DoubleVision, self).__init__(*args, **kwargs)
        self.do_glsl()

    def on_size(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = hv_blur.format(float(self.size))


class DialEffectWidget(EffectWidget):
    def __init__(self, angles, **kwargs):
        super(DialEffectWidget, self).__init__(**kwargs)

        self.shade_size = Window.height * 0.8, Window.height * 0.8
        self.add_widget(SunShading(angles))
        self.effects = [DoubleVision(size=50.0)]
        self.opacity = 0.25

    def _pos_check(self):
        if Window.width > Window.height:
            self.shade_size = Window.height * 0.8, Window.height * 0.8
        else:
            self.shade_size = Window.width * 0.8, Window.width * 0.8


class SunShading(FloatLayout):
    def __init__(self, angles, **kwargs):
        super(SunShading, self).__init__(**kwargs)

        rise_angle = angles[0]
        set_angle = angles[1]

        sun_colour = (0.9, 0.9, 0.08, 1)
        shade_colour = (0.0, 0.2, 0.4, 1)

        if angles == (0, 360):
            self.sun_one_angle_start = 0
            self.sun_one_angle_stop = 360
            self.sun_one_color = sun_colour
        elif angles == (0, 0):
            self.shade_one_angle_start = 0
            self.shade_one_angle_stop = 360
            self.shade_one_color = shade_colour
        elif rise_angle < set_angle:
            self.shade_one_angle_start = 360 - set_angle
            self.shade_one_angle_stop = 360 - rise_angle
            self.shade_one_color = shade_colour

            self.sun_one_angle_start = 0
            self.sun_one_angle_stop = 360 - set_angle
            self.sun_one_color = sun_colour
            self.sun_two_angle_start = 360 - rise_angle
            self.sun_two_angle_stop = 360
            self.sun_two_color = sun_colour

        elif rise_angle > set_angle:
            self.shade_one_angle_start = 360 - set_angle
            self.shade_one_angle_stop = 360
            self.shade_one_color = shade_colour
            self.shade_two_angle_start = 360 - rise_angle
            self.shade_two_angle_stop = 0
            self.shade_two_color = shade_colour

            self.sun_one_angle_start = 360 - rise_angle
            self.sun_one_angle_stop = 360 - set_angle
            self.sun_one_color = sun_colour

        self.shade_size = Window.height * 0.8, Window.height * 0.8

    def _size_check(self):
        self.shade_size = Window.height * 0.8, Window.height * 0.8


class SunRiseMarker(FloatLayout):
    def __init__(self, rot_angle, **kwargs):
        super(SunRiseMarker, self).__init__(**kwargs)
        self.rot_angle = rot_angle


class SunSetMarker(FloatLayout):
    def __init__(self, rot_angle, **kwargs):
        super(SunSetMarker, self).__init__(**kwargs)
        self.rot_angle = rot_angle


class NowMarker(FloatLayout):
    pass


class SeasonDial(FloatLayout):
    """
    An smaller dial layered on top of the sundial to indicate the season.
    """
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super(SeasonDial, self).__init__(**kwargs)

        self.dial_file = 'assets/seasons_dial.png'
        self.dial_size = 0.4, 0.4
        self.day_length = 86400
        self.set_season_angle()  # will this work?

        anim = Animation(angle=360, duration=self.day_length * 365.25)
        anim += Animation(angle=360, duration=self.day_length * 365.25)
        anim.repeat = True
        anim.start(self)

    def on_angle(self, item, angle):
        if angle == 360:
            item.angle = 0

    def set_season_angle(self):
        test_date = date.today()
        self.angle = round(360 / 365.25 * test_date.timetuple().tm_yday)
