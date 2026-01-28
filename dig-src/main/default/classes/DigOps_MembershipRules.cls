public class DigOps_MembershipRules {
    public class LevelConfig {
        public String levelKey;
        public Integer durationMonths;
        public Integer graceDays;
        public Boolean isPaidRequired;
    }

    public class Policy {
        public Boolean useGraceStatus;
        public Integer defaultGraceDays;
        public Boolean memberSinceResetsOnRejoin;
    }

    private static Map<String, DIG_MembershipLevel__mdt> levelByKey;
    private static List<DIG_MembershipNoticeWindow__mdt> noticeWindows;
    private static Policy policyCache;

    public static LevelConfig getLevelConfig(String levelKey) {
        ensureLevelsLoaded();
        String key = String.isBlank(levelKey) ? null : levelKey.trim();
        DIG_MembershipLevel__mdt record = key == null ? null : levelByKey.get(key);

        LevelConfig config = new LevelConfig();
        config.levelKey = key;
        config.durationMonths = record != null && record.DurationMonths__c != null
            ? Integer.valueOf(record.DurationMonths__c)
            : 12;
        Integer graceFromLevel = record != null && record.GraceDays__c != null
            ? Integer.valueOf(record.GraceDays__c)
            : null;
        Policy policy = getPolicy();
        config.graceDays = graceFromLevel != null ? graceFromLevel : policy.defaultGraceDays;
        config.isPaidRequired = record != null && record.IsPaidRequired__c != null
            ? record.IsPaidRequired__c
            : true;
        return config;
    }

    public static List<DIG_MembershipNoticeWindow__mdt> getNoticeWindows() {
        if (noticeWindows == null) {
            noticeWindows = new List<DIG_MembershipNoticeWindow__mdt>();
            for (DIG_MembershipNoticeWindow__mdt record : DIG_MembershipNoticeWindow__mdt.getAll().values()) {
                noticeWindows.add(record);
            }
            noticeWindows.sort(new NoticeWindowSorter());
        }
        return noticeWindows.deepClone(true, true, true);
    }

    public static Policy getPolicy() {
        if (policyCache != null) {
            return policyCache;
        }
        Policy policy = new Policy();
        DIG_MembershipStatusPolicy__mdt record = null;
        for (DIG_MembershipStatusPolicy__mdt candidate : DIG_MembershipStatusPolicy__mdt.getAll().values()) {
            record = candidate;
            break;
        }
        if (record != null) {
            policy.useGraceStatus = record.UseGraceStatus__c != null ? record.UseGraceStatus__c : true;
            policy.defaultGraceDays = record.DefaultGraceDays__c != null
                ? Integer.valueOf(record.DefaultGraceDays__c)
                : 30;
            policy.memberSinceResetsOnRejoin = record.MemberSinceResetsOnRejoin__c != null
                ? record.MemberSinceResetsOnRejoin__c
                : false;
        } else {
            policy.useGraceStatus = true;
            policy.defaultGraceDays = 30;
            policy.memberSinceResetsOnRejoin = false;
        }
        policyCache = policy;
        return policyCache;
    }

    private static void ensureLevelsLoaded() {
        if (levelByKey != null) {
            return;
        }
        levelByKey = new Map<String, DIG_MembershipLevel__mdt>();
        for (DIG_MembershipLevel__mdt record : DIG_MembershipLevel__mdt.getAll().values()) {
            String key = String.isBlank(record.LevelKey__c) ? record.DeveloperName : record.LevelKey__c;
            if (!String.isBlank(key)) {
                levelByKey.put(key, record);
            }
        }
    }

    private class NoticeWindowSorter implements Comparator<DIG_MembershipNoticeWindow__mdt> {
        public Integer compare(DIG_MembershipNoticeWindow__mdt a, DIG_MembershipNoticeWindow__mdt b) {
            Integer aVal = a.WindowDaysBeforeEnd__c == null ? 0 : Integer.valueOf(a.WindowDaysBeforeEnd__c);
            Integer bVal = b.WindowDaysBeforeEnd__c == null ? 0 : Integer.valueOf(b.WindowDaysBeforeEnd__c);
            if (aVal == bVal) {
                return 0;
            }
            return aVal > bVal ? -1 : 1;
        }
    }
}
