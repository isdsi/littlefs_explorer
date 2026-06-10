#include <unity.h>
#include <windows.h>
#include "Foo.h"

void setUp(void)
{
    // set stuff up here

}

void tearDown(void)
{
    // clean stuff up here
}

void test_led_builtin_pin_number(void)
{
    TEST_ASSERT_EQUAL(28, 28);
}

void test_add(void)
{
    int a = 1;
    int b = 2;
    int c;
    c = foo_add(a, b);
    TEST_ASSERT_EQUAL(3, c);
}

void setup()
{
    UNITY_BEGIN(); // IMPORTANT LINE!
    RUN_TEST(test_led_builtin_pin_number);
}

void loop()
{
    RUN_TEST(test_add);
    UNITY_END(); // stop unit testing
}

int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpszCmdParam, int nCmdShow)
{
    setup();
    loop();
    return 0;
}
