class CSkater : public CCompositeObject {
public:
    CSkater();
    float GetScriptedStat(uint32 checksum);
    CCompositeObject* GetCamera() { return nullptr; }
    bool IsLocalClient() { return true; }
    bool m_isGoofy = false;
    int m_skater_number = 0;
};
