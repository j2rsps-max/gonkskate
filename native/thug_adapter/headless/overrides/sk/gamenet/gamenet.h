#pragma once
namespace GameNet {
class Manager {
public:
    static Manager* Instance();
    bool InNetGame();
};
}
