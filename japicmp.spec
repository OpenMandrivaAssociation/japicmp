Name:		japicmp
Version:	0.23.1
Release:	1
Summary:	Compare two versions of a Java archive
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/siom79/japicmp
# Tag japicmp-base-0.23.1. The catalog coordinate
# me.champeau.gradle:japicmp-gradle-plugin 0.4.6 depends on this
# artifact. The archive omits the two test jars old.jar and new.jar.
# Main sources are compiled with javac. The Maven tool is not invoked.
# The Maven plugin and Ant task modules are not built.
Source0:	japicmp-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	mvn(org.javassist:javassist)
BuildRequires:	mvn(com.google.guava:guava)
BuildRequires:	mvn(javax.xml.bind:jaxb-api)
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem

%description
com.github.siom79.japicmp:japicmp %{version}. JarArchiveComparator
reports removed, added, and changed classes. The main sources are
compiled with javac at release 8 against the system javassist, Guava,
and JAXB API jars.

%prep
%autosetup -n japicmp-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
find japicmp/src/main/java -name '*.java' | sort > sources.list
test "$(wc -l < sources.list)" -eq 133

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
CP=%{_javadir}/javassist.jar:%{_javadir}/guava.jar:%{_javadir}/javax.xml.bind.jar
for extra in \
	%{_javadir}/javassist.jar \
	%{_javadir}/guava.jar \
	%{_javadir}/javax.xml.bind.jar
do
	test -s "$extra"
done
mkdir -p classes
javac --release 8 -Xlint:-options -encoding UTF-8 -cp "$CP" -d classes @sources.list
test "$(find classes -name '*.class' | wc -l)" -eq 205
cp -a japicmp/src/main/resources/. classes/
test -s classes/style.css
test -s classes/html/methods.html
javap -v -classpath classes japicmp.cmp.JarArchiveComparator | grep -F -q 'major version: 52'
javap -v -classpath classes japicmp.model.JApiClass | grep -F -q 'major version: 52'
printf '%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: japicmp' > manifest.mf
jar cfm japicmp.jar manifest.mf -C classes .
jar i japicmp.jar
jar tf japicmp.jar | grep -F -q 'japicmp/cmp/JarArchiveComparator.class'
jar tf japicmp.jar | grep -F -q 'style.css'
desc=$(jar --describe-module --file japicmp.jar)
printf '%s\n' "$desc" | grep -F -q 'japicmp'
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	printf '%s\n' "$desc"
	exit 1
fi

cat > japicmp.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.github.siom79.japicmp</groupId>
  <artifactId>japicmp</artifactId>
  <version>%{version}</version>
  <name>japicmp</name>
  <description>Compare two versions of a jar archive.</description>
  <url>https://github.com/siom79/japicmp</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.javassist</groupId>
      <artifactId>javassist</artifactId>
      <version>3.33.0-GA</version>
    </dependency>
    <dependency>
      <groupId>com.google.guava</groupId>
      <artifactId>guava</artifactId>
      <version>33.6.0-jre</version>
    </dependency>
    <dependency>
      <groupId>javax.xml.bind</groupId>
      <artifactId>jaxb-api</artifactId>
      <version>2.4.0.b180830.0359</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact japicmp.pom:japicmp.jar \
	--file-name japicmp \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/com.github.siom79.japicmp/japicmp.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "japicmp"' "$idx"
test -s %{buildroot}%{_javadir}/japicmp.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
JAR=%{buildroot}%{_javadir}/japicmp.jar
test -s "$JAR"
CP="$JAR:%{_javadir}/javassist.jar:%{_javadir}/guava.jar:%{_javadir}/javax.xml.bind.jar"
mkdir -p check/oldsrc/sample check/newsrc/sample check/old check/new
cat > check/oldsrc/sample/Hello.java << 'EOF'
package sample;
public class Hello {
	public String hi() { return "hi"; }
	public String keep() { return "keep"; }
}
EOF
cat > check/newsrc/sample/Hello.java << 'EOF'
package sample;
public class Hello {
	public String keep() { return "keep"; }
}
EOF
javac --release 8 -Xlint:-options -d check/old check/oldsrc/sample/Hello.java
javac --release 8 -Xlint:-options -d check/new check/newsrc/sample/Hello.java
jar cf check/old.jar -C check/old sample
jar cf check/new.jar -C check/new sample
cat > check/Smoke.java << 'EOF'
import japicmp.cmp.JarArchiveComparator;
import japicmp.cmp.JarArchiveComparatorOptions;
import japicmp.cmp.JApiCmpArchive;
import japicmp.model.JApiChangeStatus;
import japicmp.model.JApiClass;
import japicmp.model.JApiMethod;

import java.io.File;
import java.util.List;

public class Smoke {
	public static void main(String[] args) {
		JarArchiveComparator cmp = new JarArchiveComparator(new JarArchiveComparatorOptions());
		List<JApiClass> classes = cmp.compare(
			new JApiCmpArchive(new File(args[0]), "1"),
			new JApiCmpArchive(new File(args[1]), "2"));
		int removed = 0;
		for (JApiClass cls : classes) {
			if (!"sample.Hello".equals(cls.getFullyQualifiedName())) {
				continue;
			}
			for (JApiMethod method : cls.getMethods()) {
				if ("hi".equals(method.getName()) && method.getChangeStatus() == JApiChangeStatus.REMOVED) {
					removed++;
				}
			}
		}
		System.out.println("japicmp_ok " + removed);
	}
}
EOF
javac --release 8 -Xlint:-options -cp "$CP" -d check check/Smoke.java
"$JAVA_HOME/bin/java" -cp "check:$CP" Smoke check/old.jar check/new.jar > check/out.txt
cat check/out.txt
grep -F -qx 'japicmp_ok 1' check/out.txt

%files -f .mfiles
%doc README.md
%license LICENSE
