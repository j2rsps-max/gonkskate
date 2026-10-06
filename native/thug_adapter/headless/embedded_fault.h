#pragma once
#include <stdexcept>
namespace Headless {
struct Fault:std::runtime_error {
    int code;
    Fault(int status,const char* message):std::runtime_error(message),code(status){}
};
}
